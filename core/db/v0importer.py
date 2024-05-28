from json import loads
from os.path import exists
from pathlib import Path
from uuid import UUID, uuid4

import aiosqlite

from core.db.models import Branch, Project, ProjectState
from core.db.models.project_state import TaskStatus
from core.db.session import SessionManager
from core.disk.vfs import MemoryVFS
from core.log import get_logger
from core.state.state_manager import StateManager

log = get_logger(__name__)


class ImporterStateManager(StateManager):
    async def init_file_system(self, load_existing: bool) -> MemoryVFS:
        """
        Initialize in-memory file system.

        We don't want to overwrite all the files on disk while importing
        the legacy database, as this could overwrite new changes that the
        user might have done in the meantime. Project loading will handle that.
        """
        return MemoryVFS()


class LegacyDatabaseImporter:
    def __init__(self, session_manager: SessionManager, dbpath: str):
        self.session_manager = session_manager
        self.state_manager = ImporterStateManager(self.session_manager, None)
        self.dbpath = dbpath
        self.conn = None

        if not exists(dbpath):
            raise FileNotFoundError(f"File not found: {dbpath}")

    async def import_database(self):
        try:
            info = await self.load_legacy_database()
        except Exception as err:  # noqa
            print(f"Failed to load legacy database {self.dbpath}: {err}")
            return
        n = await self.save_to_new_database(info)
        print(f"Successfully imported {n} projects from {self.dbpath}")

    async def load_legacy_database(self):
        async with aiosqlite.connect(self.dbpath) as conn:
            self.conn = conn
            is_valid = await self.verify_schema()
            if not is_valid:
                raise ValueError(f"Database {self.dbpath} doesn't look like a GPT-Pilot database")

            apps = await self.get_apps()
            info = {}
            for app_id in apps:
                app_info = await self.get_app_info(app_id)
                info[app_id] = {
                    "name": apps[app_id],
                    **app_info,
                }

        return info

    async def verify_schema(self) -> bool:
        tables = set()
        async with self.conn.execute("select name from sqlite_master where type = 'table'") as cursor:
            async for row in cursor:
                tables.add(row[0])

        return "app" in tables and "development_steps" in tables

    async def get_apps(self) -> dict[str, str]:
        apps = {}
        async with self.conn.execute("select id, name, status from app") as cursor:
            async for id, name, status in cursor:
                if status == "coding":
                    apps[id] = name
        return apps

    async def get_app_info(self, app_id: str) -> dict:
        app_info = {
            "initial_prompt": None,
            "architecture": None,
            "tasks": [],
        }

        async with self.conn.execute("select architecture from architecture where app_id = ?", (app_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                app_info["architecture"] = loads(row[0])

        async with self.conn.execute("select prompt from project_description where app_id = ?", (app_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                app_info["initial_prompt"] = row[0]

        async with self.conn.execute(
            "select id, prompt_path, prompt_data, messages, llm_response from development_steps "
            "where app_id = ? order by created_at asc",
            (app_id,),
        ) as cursor:
            async for row in cursor:
                dev_step_id, prompt_path, prompt_data, messages, llm_response = row
                if prompt_path == "development/task/breakdown.prompt":
                    task_info = await self.get_task_info(dev_step_id, prompt_data, llm_response)
                    app_info["tasks"].append(task_info)

        return app_info

    async def get_task_info(self, dev_step_id, prompt_data_json: str, llm_response: dict) -> dict:
        prompt_data = loads(prompt_data_json)
        current_feature = prompt_data.get("current_feature")
        previous_features = prompt_data.get("previous_features") or []
        tasks = prompt_data["development_tasks"]
        current_task_index = prompt_data["current_task_index"]
        current_task = tasks[current_task_index]
        instructions = llm_response
        files = await self.get_task_files(dev_step_id)
        return {
            "current_feature": current_feature,
            "previous_features": previous_features,
            "tasks": tasks,
            "current_task_index": current_task_index,
            "current_task": current_task,
            "instructions": instructions,
            "files": files,
        }

    async def get_task_files(self, dev_step_id: int):
        files = {}

        async with self.conn.execute(
            "select content, path, name, description from file_snapshot "
            "inner join file on file_snapshot.file_id = file.id "
            "where file_snapshot.development_step_id = ?",
            (dev_step_id,),
        ) as cursor:
            async for row in cursor:
                content, path, name, description = row
                file_path = Path(path + "/" + name).as_posix() if path else name
                try:
                    if isinstance(content, bytes):
                        content = content.decode("utf-8")
                except:  # noqa
                    # skip binary file
                    continue
                files[file_path] = {
                    "description": description or None,
                    "content": content,
                }

        return files

    async def save_to_new_database(self, info: dict) -> int:
        """
        Save projects to the new database

        :param info: A dictionary with app_id as key and app info as value.
        :return: Number of projects saved to the new database.
        """
        async with self.session_manager as session:
            projects = await Project.get_all_projects(session)

        for project in projects:
            imported_app = info.pop(project.id.hex, None)
            if imported_app:
                log.info(f"Project {project.name} already exists in the new database, skipping")

        n = 0
        for app_id, app_info in info.items():
            await self.save_app(app_id, app_info)
            n += 1
        return n

    async def save_app(self, app_id: str, app_info: dict):
        log.info(f"Importing app {app_info['name']} (id={app_id}) ...")

        async with self.session_manager as session:
            project = Project(id=UUID(app_id), name=app_info["name"])
            branch = Branch(project=project)
            state = ProjectState.create_initial_state(branch)

            spec = state.specification
            spec.description = app_info["initial_prompt"]
            spec.architecture = app_info["architecture"]["architecture"]
            spec.system_dependencies = app_info["architecture"]["system_dependencies"]
            spec.package_dependencies = app_info["architecture"]["package_dependencies"]
            spec.template = app_info["architecture"].get("template")

            session.add(project)
            await session.commit()

        project = await self.state_manager.load_project(project_id=app_id)

        # It is much harder to import all tasks and keep features/tasks lists in sync, so
        # we only support importing the latest task.
        if app_info["tasks"]:
            await self.save_latest_task(app_info["tasks"][-1])

        # This just closes the session and removes the last (incomplete) state.
        # Everything else should already be safely comitted.
        await self.state_manager.rollback()

    async def save_latest_task(self, task: dict):
        sm = self.state_manager
        state = sm.current_state

        state.epics = [
            {
                "id": uuid4().hex,
                "name": "Initial Project",
                "description": state.specification.description,
                "summary": None,
                "completed": bool(task["previous_features"]) or (task["current_feature"] is not None),
                "complexity": "hard",
            }
        ]

        for i, feature in enumerate(task["previous_features"]):
            state.epics += [
                {
                    "id": uuid4().hex,
                    "name": f"Feature #{i + 1}",
                    "description": feature["summary"],  # FIXME: is this good enough
                    "summary": None,
                    "completed": True,
                    "complexity": "hard",
                }
            ]

        if task["current_feature"]:
            state.epics = state.epics + [
                {
                    "id": uuid4().hex,
                    "name": f"Feature #{len(state.epics)}",
                    "description": task["current_feature"],
                    "summary": None,
                    "completed": False,
                    "complexity": "hard",
                }
            ]

        current_task_index = task["current_task_index"]
        state.tasks = [
            {
                "id": uuid4().hex,
                "description": task_info["description"],
                "instructions": None,
                "status": TaskStatus.DONE if current_task_index > i else TaskStatus.TODO,
            }
            for i, task_info in enumerate(task["tasks"])
        ]
        state.tasks[current_task_index]["instructions"] = task["instructions"]
        await sm.current_session.commit()

        # Reload project at the initialized state to reinitialize the next state
        await self.state_manager.load_project(project_id=state.branch.project.id, step_index=state.step_index)

        await self.save_task_files(task["files"])
        await self.state_manager.commit()

    async def save_task_files(self, files: dict):
        for path, file_info in files.items():
            await self.state_manager.save_file(
                path,
                file_info["content"],
                metadata={
                    "description": file_info["description"],
                    "references": [],
                },
            )
