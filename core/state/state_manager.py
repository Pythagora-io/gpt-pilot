import asyncio
import os.path
import traceback
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import inspect, select
from tenacity import retry, stop_after_attempt, wait_fixed

from core.config import FileSystemType, get_config
from core.db.models import Branch, ExecLog, File, FileContent, LLMRequest, Project, ProjectState, UserInput
from core.db.models.specification import Complexity, Specification
from core.db.session import SessionManager
from core.disk.ignore import IgnoreMatcher
from core.disk.vfs import LocalDiskVFS, MemoryVFS, VirtualFileSystem
from core.llm.request_log import LLMRequestLog, LLMRequestStatus
from core.log import get_logger
from core.proc.exec_log import ExecLog as ExecLogData
from core.telemetry import telemetry
from core.ui.base import UIBase
from core.ui.base import UserInput as UserInputData

if TYPE_CHECKING:
    from core.agents.base import BaseAgent

log = get_logger(__name__)


class StateManager:
    """
    Manages loading, updating and saving project states.

    All project state references reading the current state
    should use `StateManager.current` attribute. All changes
    to the state should be done through the `StateManager.next`
    attribute.
    """

    current_state: Optional[ProjectState]
    next_state: Optional[ProjectState]

    def __init__(self, session_manager: SessionManager, ui: Optional[UIBase] = None):
        self.session_manager = session_manager
        self.ui = ui
        self.file_system = None
        self.project = None
        self.branch = None
        self.current_state = None
        self.next_state = None
        self.current_session = None
        self.blockDb = False
        self.git_available = False
        self.git_used = False
        self.options = {}

    @asynccontextmanager
    async def db_blocker(self):
        while self.blockDb:
            await asyncio.sleep(0.1)  # Wait if blocked

        try:
            self.blockDb = True  # Set the block
            yield
        finally:
            self.blockDb = False  # Unset the block

    async def list_projects(self) -> list[Project]:
        """
        List projects with branches

        :return: List of projects with all their branches.
        """
        async with self.session_manager as session:
            return await Project.get_all_projects(session)

    async def create_project(self, name: str, folder_name: Optional[str] = None) -> Project:
        """
        Create a new project and set it as the current one.

        :param name: Project name.
        :return: The Project object.
        """
        session = await self.session_manager.start()
        project = Project(name=name, folder_name=folder_name)
        branch = Branch(project=project)
        state = ProjectState.create_initial_state(branch)
        session.add(project)

        # This is needed as we have some behavior that traverses the files
        # even for a new project, eg. offline changes check and stats updating
        await state.awaitable_attrs.files

        await session.commit()

        log.info(
            f'Created new project "{name}" (id={project.id}) '
            f'with default branch "{branch.name}" (id={branch.id}) '
            f"and initial state id={state.id} (step_index={state.step_index})"
        )
        await telemetry.trace_code_event("create-project", {"name": name})

        self.current_session = session
        self.current_state = state
        self.next_state = state
        self.project = project
        self.branch = branch
        self.file_system = await self.init_file_system(load_existing=False)
        return project

    async def delete_project(self, project_id: UUID) -> bool:
        session = await self.session_manager.start()
        rows = await Project.delete_by_id(session, project_id)
        if rows > 0:
            await Specification.delete_orphans(session)
            await FileContent.delete_orphans(session)

        await session.commit()

        if rows > 0:
            log.info(f"Deleted project {project_id}.")
        return bool(rows)

    async def load_project(
        self,
        *,
        project_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        step_index: Optional[int] = None,
    ) -> Optional[ProjectState]:
        """
        Load project state from the database.

        If `branch_id` is provided, load the latest state of the branch.
        Otherwise, if `project_id` is provided, load the latest state of
        the `main` branch in the project.

        If `step_index' is provided, load the state at the given step
        of the branch instead of the last one.

        The returned ProjectState will have branch and branch.project
        relationships preloaded. All other relationships must be
        explicitly loaded using ProjectState.awaitable_attrs or
        AsyncSession.refresh.

        :param project_id: Project ID (keyword-only, optional).
        :param branch_id: Branch ID (keyword-only, optional).
        :param step_index: Step index within the branch (keyword-only, optional).
        :return: The ProjectState object if found, None otherwise.
        """

        if self.current_session:
            log.info("Current session exists, rolling back changes.")
            await self.rollback()

        state = None
        session = await self.session_manager.start()

        if branch_id is not None:
            branch = await Branch.get_by_id(session, branch_id)
            if branch is not None:
                if step_index:
                    state = await branch.get_state_at_step(step_index)
                else:
                    state = await branch.get_last_state()

        elif project_id is not None:
            project = await Project.get_by_id(session, project_id)
            if project is not None:
                branch = await project.get_branch()
                if branch is not None:
                    if step_index:
                        state = await branch.get_state_at_step(step_index)
                    else:
                        state = await branch.get_last_state()
        else:
            raise ValueError("Project or branch ID must be provided.")

        if state is None:
            await self.session_manager.close()
            log.debug(
                f"Unable to load project state (project_id={project_id}, branch_id={branch_id}, step_index={step_index})"
            )
            return None

        # TODO: in the future, we might want to create a new branch here?
        await state.delete_after()
        await session.commit()

        self.current_session = session
        self.current_state = state
        self.branch = state.branch
        self.project = state.branch.project
        self.next_state = await state.create_next_state()
        self.file_system = await self.init_file_system(load_existing=True)
        log.debug(
            f"Loaded project {self.project} ({self.project.id}) "
            f"branch {self.branch} ({self.branch.id}"
            f"step {state.step_index} (state id={state.id})"
        )

        if self.current_state.current_epic and self.current_state.current_task and self.ui:
            await self.ui.send_epics_and_tasks(
                self.current_state.current_epic.get("sub_epics"),
                self.current_state.tasks,
            )
            source = self.current_state.current_epic.get("source", "app")
            await self.ui.send_task_progress(
                self.current_state.tasks.index(self.current_state.current_task) + 1,
                len(self.current_state.tasks),
                self.current_state.current_task["description"],
                source,
                "in-progress",
                self.current_state.get_source_index(source),
                self.current_state.tasks,
            )

        telemetry.set(
            "architecture",
            {
                "system_dependencies": self.current_state.specification.system_dependencies,
                "package_dependencies": self.current_state.specification.package_dependencies,
            },
        )
        telemetry.set("example_project", self.current_state.specification.example_project)
        telemetry.set("is_complex_app", self.current_state.specification.complexity != Complexity.SIMPLE)
        telemetry.set("templates", self.current_state.specification.templates)

        return self.current_state

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def commit_with_retry(self):
        try:
            await self.current_session.commit()
        except Exception as e:
            log.error(f"Commit failed: {str(e)}")
            raise

    async def commit(self) -> ProjectState:
        """
        Commit the new project state to the database.

        This commits `next_state` to the database, making the changes
        permanent, then creates a new state for further changes.

        :return: The committed state.
        """
        try:
            if self.next_state is None:
                raise ValueError("No state to commit.")
            if self.current_session is None:
                raise ValueError("No database session open.")

            log.debug("Committing session")
            await self.commit_with_retry()
            log.debug("Session committed successfully")

            # Having a shorter-lived sessions is considered a good practice in SQLAlchemy,
            # so we close and recreate the session for each state. This uses db
            # connection from a connection pool, so it is fast. Note that SQLite uses
            # no connection pool by default because it's all in-process so it's fast anyway.
            self.current_session.expunge_all()
            await self.session_manager.close()
            self.current_session = await self.session_manager.start()

            self.current_state = self.next_state
            self.current_session.add(self.next_state)
            self.next_state = await self.current_state.create_next_state()

            # After the next_state becomes the current_state, we need to load
            # the FileContent model, which was previously loaded by the load_project(),
            # but is not populated by the `create_next_state()`
            for f in self.current_state.files:
                await f.awaitable_attrs.content

            telemetry.inc("num_steps")

            # FIXME: write a test to verify files (and file content) are preloaded
            return self.current_state

        except Exception as e:
            log.error(f"Error during commit: {str(e)}")
            log.error(traceback.format_exc())
            raise

    async def rollback(self):
        """
        Abandon (rollback) the next state changes.
        """
        if not self.current_session:
            return
        await self.current_session.rollback()
        await self.session_manager.close()
        self.current_session = None
        return

    async def log_llm_request(self, request_log: LLMRequestLog, agent: Optional["BaseAgent"] = None):
        """
        Log the request to the next state.

        Note: contrary to most other methods, this stores the information
        to the CURRENT state, not the next one. As the requests/responses
        depend on the current state, it makes it easier to analyze the
        database by just looking at a single project state later.

        :param request_log: The request log to log.
        """
        async with self.db_blocker():
            try:
                telemetry.record_llm_request(
                    request_log.prompt_tokens + request_log.completion_tokens,
                    request_log.duration,
                    request_log.status != LLMRequestStatus.SUCCESS,
                )
                LLMRequest.from_request_log(self.current_state, agent, request_log)

            except Exception as e:
                if self.ui:
                    await self.ui.send_message(f"An error occurred: {e}")

    async def log_user_input(self, question: str, response: UserInputData):
        """
        Log the user input to the current state.

        Note: contrary to most other methods, this stores the information
        to the CURRENT state, not the next one. As the user interactions
        depend on the current state, it makes it easier to analyze the
        database by just looking at a single project state later.

        :param question: The question asked.
        :param response: The user response.
        """
        telemetry.inc("num_inputs")
        UserInput.from_user_input(self.current_state, question, response)

    async def log_command_run(self, exec_log: ExecLogData):
        """
        Log the command run to the current state.

        Note: contrary to most other methods, this stores the information
        to the CURRENT state, not the next one. As the command execution
        depend on the current state, it makes it easier to analyze the
        database by just looking at a single project state later.

        :param exec_log: The command execution log.
        """
        telemetry.inc("num_commands")
        ExecLog.from_exec_log(self.current_state, exec_log)

    async def log_event(self, type: str, **kwargs):
        """
        Log an event like:


        * start of epic
        * start of task
        * start of iteration
        * end of task
        * end of epic
        * loop detected
        """
        # TODO: implement this
        # Consider seting this/orchestrator so that the side effect is to send
        # the update to the UI (vscode extension)

    async def log_task_completed(self):
        telemetry.inc("num_tasks")
        if not self.next_state.unfinished_tasks:
            if len(self.current_state.epics) == 1:
                telemetry.set("end_result", "success:frontend")
            elif len(self.current_state.epics) == 2:
                telemetry.set("end_result", "success:initial-project")
            else:
                telemetry.set("end_result", "success:feature")
            await telemetry.send()

    async def get_file_by_path(self, path: str) -> Optional[File]:
        """
        Get a file from the current project state, by the file path.

        :param path: The file path.
        :return: The file object, or None if not found.
        """
        return self.current_state.get_file_by_path(path)

    async def save_file(
        self,
        path: str,
        content: str,
        metadata: Optional[dict] = None,
        from_template: bool = False,
    ):
        """
        Save a file to the project.

        Note that the file is saved to the file system immediately, but in
        database it may be rolled back if `next_state` is never committed.

        :param path: The file path.
        :param content: The file content.
        :param metadata: Optional metadata (eg. description) to save with the file.
        :param from_template: Whether the file is part of a template.
        """
        try:
            original_content = self.file_system.read(path)
        except ValueError:
            original_content = ""

        # FIXME: VFS methods should probably be async
        self.file_system.save(path, content)

        hash = self.file_system.hash_string(content)
        async with self.db_blocker():
            file_content = await FileContent.store(self.current_session, hash, content)

        file = self.next_state.save_file(path, file_content)
        # if self.ui and not from_template:
        #     await self.ui.open_editor(self.file_system.get_full_path(path))
        if metadata:
            file.meta = metadata

        if not from_template:
            delta_lines = len(content.splitlines()) - len(original_content.splitlines())
            telemetry.inc("created_lines", delta_lines)

    async def init_file_system(self, load_existing: bool) -> VirtualFileSystem:
        """
        Initialize file system interface for the new or loaded project.

        When creating a new project, `load_existing` should be False to ensure a
        new unique project folder is created. When loading an existing project,
        `load_existing` should be True to allow using already-existing folder
        with the project files. If the folder doesn't exist, it will be created.

        This also initializes the ignore mechanism, so that files are correctly
        ignored as configured.

        :param load_existing: Whether to load existing files from the file system.
        :return: The file system interface.
        """
        config = get_config()

        if config.fs.type == FileSystemType.MEMORY:
            return MemoryVFS()

        if config.fs.type != FileSystemType.LOCAL:
            raise ValueError(f"Unsupported file system type: {config.fs.type}")

        while True:
            root = self.get_full_project_root()
            ignore_matcher = IgnoreMatcher(
                root,
                config.fs.ignore_paths,
                ignore_size_threshold=config.fs.ignore_size_threshold,
            )

            try:
                return LocalDiskVFS(root, allow_existing=load_existing, ignore_matcher=ignore_matcher)
            except FileExistsError:
                self.project.folder_name = self.project.folder_name + "-" + uuid4().hex[:7]
                log.warning(f"Directory {root} already exists, changing project folder to {self.project.folder_name}")
                await self.current_session.commit()

    def get_full_project_root(self) -> str:
        """
        Get the full path to the project root folder.

        :return: The full path to the project root folder.
        """
        config = get_config()

        if self.project is None:
            raise ValueError("No project loaded")
        return os.path.join(config.fs.workspace_root, self.project.folder_name)

    async def import_files(self) -> tuple[list[File], list[File]]:
        """
        Scan the file system, import new/modified files, delete removed files.

        The files are saved to / removed from `next_state`, but not committed
        to database until the new state is committed.

        :return: Tuple with the list of imported files and the list of removed files.
        """
        known_files = {file.path: file for file in self.current_state.files}
        files_in_workspace = set()
        imported_files = []
        removed_files = []

        for path in self.file_system.list():
            files_in_workspace.add(path)
            content = self.file_system.read(path)
            saved_file = known_files.get(path)

            if saved_file and saved_file.content.content == content:
                continue

            # TODO: unify this with self.save_file() / refactor that whole bit
            hash = self.file_system.hash_string(content)
            log.debug(f"Importing file {path} (hash={hash}, size={len(content)} bytes)")
            file_content = await FileContent.store(self.current_session, hash, content)
            file = self.next_state.save_file(path, file_content, external=True)
            imported_files.append(file)

        for path, file in known_files.items():
            if path not in files_in_workspace:
                log.debug(f"File {path} was removed from workspace, deleting from project")
                next_state_file = self.next_state.get_file_by_path(path)
                self.next_state.files.remove(next_state_file)
                removed_files.append(file.path)

        return imported_files, removed_files

    async def restore_files(self) -> list[File]:
        """
        Restore files from the database to VFS.

        Warning: this could overwrite user's files on disk!

        :return: List of restored files.
        """
        known_files = {file.path: file for file in self.current_state.files}
        files_in_workspace = self.file_system.list()

        for disk_f in files_in_workspace:
            if disk_f not in known_files:
                self.file_system.remove(disk_f)

        restored_files = []
        for path, file in known_files.items():
            restored_files.append(file)
            self.file_system.save(path, file.content.content)

        return restored_files

    async def get_modified_files(self) -> list[str]:
        """
        Return a list of new or modified files from the file system.

        :return: List of paths for new or modified files.
        """

        modified_files = []
        files_in_workspace = self.file_system.list()
        for path in files_in_workspace:
            content = self.file_system.read(path)
            saved_file = self.current_state.get_file_by_path(path)
            if saved_file and saved_file.content.content == content:
                continue
            modified_files.append(path)

        # Handle files removed from disk
        await self.current_state.awaitable_attrs.files
        for db_file in self.current_state.files:
            if db_file.path not in files_in_workspace:
                modified_files.append(db_file.path)

        return modified_files

    async def get_modified_files_with_content(self) -> list[dict]:
        """
        Return a list of new or modified files from the file system,
        including their paths, old content, and new content.

        :return: List of dictionaries containing paths, old content,
                and new content for new or modified files.
        """

        modified_files = []
        files_in_workspace = self.file_system.list()

        for path in files_in_workspace:
            content = self.file_system.read(path)
            saved_file = self.current_state.get_file_by_path(path)

            # If there's a saved file, serialize its content; otherwise, set it to None
            saved_file_content = saved_file.content.content if saved_file else None

            if saved_file_content == content:
                continue

            modified_files.append(
                {
                    "path": path,
                    "file_old": saved_file_content,  # Serialized content
                    "file_new": content,
                }
            )

        # Handle files removed from disk
        await self.current_state.awaitable_attrs.files
        for db_file in self.current_state.files:
            if db_file.path not in files_in_workspace:
                modified_files.append(
                    {
                        "path": db_file.path,
                        "file_old": db_file.content.content,  # Serialized content
                        "file_new": "",  # Empty string as the file is removed
                    }
                )

        return modified_files

    def workspace_is_empty(self) -> bool:
        """
        Returns whether the workspace has any files in them or is empty.
        """
        return not bool(self.file_system.list())

    def get_implemented_pages(self) -> list[str]:
        """
        Get the list of implemented pages.

        :return: List of implemented pages.
        """
        # TODO - use self.current_state plus response from the FE iteration
        page_files = [file.path for file in self.next_state.files if "client/src/pages" in file.path]
        return page_files

    async def update_implemented_pages_and_apis(self):
        modified = False
        pages = self.get_implemented_pages()
        apis = await self.get_apis()

        # Get the current state of pages and apis from knowledge_base
        current_pages = self.next_state.knowledge_base.get("pages", None)
        current_apis = self.next_state.knowledge_base.get("apis", None)

        # Check if pages or apis have changed
        if pages != current_pages or apis != current_apis:
            modified = True

        if modified:
            self.next_state.knowledge_base["pages"] = pages
            self.next_state.knowledge_base["apis"] = apis
            self.next_state.flag_knowledge_base_as_modified()
            await self.ui.knowledge_base_update(self.next_state.knowledge_base)

    async def update_utility_functions(self, utility_function: dict):
        """
        Update the knowledge base with the utility function.

        :param utility_function: Utility function to update.
        """
        matched = False
        for kb_util_func in self.next_state.knowledge_base.get("utility_functions", []):
            if (
                utility_function["function_name"] == kb_util_func["function_name"]
                and utility_function["file"] == kb_util_func["file"]
            ):
                kb_util_func["return_value"] = utility_function["return_value"]
                kb_util_func["input_value"] = utility_function["input_value"]
                kb_util_func["status"] = utility_function["status"]
                matched = True
                self.next_state.flag_knowledge_base_as_modified()
                break

        if not matched:
            if "utility_functions" not in self.next_state.knowledge_base:
                self.next_state.knowledge_base["utility_functions"] = []
            self.next_state.knowledge_base["utility_functions"].append(utility_function)

        self.next_state.flag_knowledge_base_as_modified()
        await self.ui.knowledge_base_update(self.next_state.knowledge_base)

    async def get_apis(self) -> list[dict]:
        """
        Get the list of APIs.

        :return: List of APIs.
        """
        apis = []
        for file in self.next_state.files:
            if "client/src/api" not in file.path:
                continue
            session = inspect(file).async_session
            result = await session.execute(select(FileContent).where(FileContent.id == file.content_id))
            file_content = result.scalar_one_or_none()
            content = file_content.content
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if "// Description:" in line:
                    # TODO: Make this better!!!
                    description = line.split("Description:")[1]
                    endpoint = lines[i + 1].split("Endpoint:")[1] if len(lines[i + 1].split("Endpoint:")) > 1 else ""
                    request = lines[i + 2].split("Request:")[1] if len(lines[i + 2].split("Request:")) > 1 else ""
                    response = lines[i + 3].split("Response:")[1] if len(lines[i + 3].split("Response:")) > 1 else ""
                    backend = (
                        next(
                            (
                                api
                                for api in self.current_state.knowledge_base.get("apis", [])
                                if api["endpoint"] == endpoint.strip()
                            ),
                            {},
                        )
                        .get("locations", {})
                        .get("backend", None)
                    )
                    apis.append(
                        {
                            "description": description.strip(),
                            "endpoint": endpoint.strip(),
                            "request": request.strip(),
                            "response": response.strip(),
                            "locations": {
                                "frontend": {
                                    "path": file.path,
                                    "line": i - 1,
                                },
                                "backend": backend,
                            },
                            "status": "implemented" if backend is not None else "mocked",
                        }
                    )
        return apis

    async def update_apis(self, files_with_implemented_apis: list[dict] = []):
        """
        Update the list of APIs.

        """
        apis = await self.get_apis()
        for file in files_with_implemented_apis:
            for endpoint in file["related_api_endpoints"]:
                api = next((api for api in apis if (endpoint in api["endpoint"])), None)
                if api is not None:
                    api["status"] = "implemented"
                    api["locations"]["backend"] = {
                        "path": file["path"],
                        "line": file["line"],
                    }
        self.next_state.knowledge_base["apis"] = apis
        self.next_state.flag_knowledge_base_as_modified()
        await self.ui.knowledge_base_update(self.next_state.knowledge_base)

    @staticmethod
    def get_input_required(content: str, file_path: str) -> list[int]:
        """
        Get the list of lines containing INPUT_REQUIRED keyword.

        :param content: The file content to search.
        :param file_path: The file path.
        :return: Indices of lines with INPUT_REQUIRED keyword, starting from 1.
        """
        lines = []

        if ".env" not in file_path:
            return lines

        for i, line in enumerate(content.splitlines(), start=1):
            if "INPUT_REQUIRED" in line:
                lines.append(i)

        return lines


__all__ = ["StateManager"]
