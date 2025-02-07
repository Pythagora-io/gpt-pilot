import os

from core.agents.convo import AgentConvo
from core.config.magic_words import GITIGNORE_CONTENT
from core.ui.base import pythagora_source


class GitMixin:
    """
    Mixin class for git commands
    """

    async def check_git_installed(self) -> bool:
        """Check if git is installed on the system."""
        status_code, _, _ = await self.process_manager.run_command("git --version", show_output=False)
        git_available = status_code == 0
        self.state_manager.git_available = git_available
        return git_available

    async def is_git_initialized(self) -> bool:
        """Check if git is initialized in the workspace."""
        workspace_path = self.state_manager.get_full_project_root()

        status_code, _, _ = await self.process_manager.run_command(
            "git rev-parse --git-dir --is-inside-git-dir",
            cwd=workspace_path,
            show_output=False,
        )
        # Will return status code 0 only if .git exists in the current directory
        git_used = status_code == 0 and os.path.exists(os.path.join(workspace_path, ".git"))
        self.state_manager.git_used = git_used
        return git_used

    async def init_git_if_needed(self) -> bool:
        """
        Initialize git repository if it hasn't been initialized yet.
        Returns True if initialization was needed and successful.
        """

        workspace_path = self.state_manager.get_full_project_root()
        if await self.is_git_initialized():
            return False

        answer = await self.ui.ask_question(
            "Git is not initialized for this project. Do you want to initialize it now?",
            buttons={"yes": "Yes", "no": "No"},
            default="yes",
            buttons_only=True,
            source=pythagora_source,
        )

        if answer.button == "no":
            return False
        else:
            status_code, _, stderr = await self.process_manager.run_command("git init", cwd=workspace_path)
            if status_code != 0:
                raise RuntimeError(f"Failed to initialize git repository: {stderr}")

            gitignore_path = os.path.join(workspace_path, ".gitignore")
            try:
                with open(gitignore_path, "w") as f:
                    f.write(GITIGNORE_CONTENT)
            except Exception as e:
                raise RuntimeError(f"Failed to create .gitignore file: {str(e)}")

            # First check if there are any changes to commit
            status_code, stdout, stderr = await self.process_manager.run_command(
                "git status --porcelain",
                cwd=workspace_path,
            )

            if status_code == 0 and stdout.strip():  # If there are changes (stdout is not empty)
                # Stage all files
                status_code, _, stderr = await self.process_manager.run_command(
                    "git add .",
                    cwd=workspace_path,
                )
                if status_code != 0:
                    raise RuntimeError(f"Failed to stage files: {stderr}")

                # Create initial commit
                status_code, _, stderr = await self.process_manager.run_command(
                    'git commit -m "initial commit"', cwd=workspace_path
                )
                if status_code != 0:
                    raise RuntimeError(f"Failed to create initial commit: {stderr}")

            self.state_manager.git_used = True
            return True

    async def git_commit(self) -> None:
        """
        Create a git commit with the specified message.
        Raises RuntimeError if the commit fails.
        """
        workspace_path = self.state_manager.get_full_project_root()

        # Check if there are any changes to commit
        status_code, git_status, stderr = await self.process_manager.run_command(
            "git status --porcelain",
            cwd=workspace_path,
            show_output=False,
        )
        if status_code != 0:
            raise RuntimeError(f"Failed to get git status: {stderr}")

        if not git_status.strip():
            return

        answer = await self.ui.ask_question(
            "Do you want to create new git commit?",
            buttons={"yes": "Yes", "no": "No"},
            default="yes",
            buttons_only=True,
            source=pythagora_source,
        )

        if answer.button == "no":
            return

        # Stage all changes
        status_code, _, stderr = await self.process_manager.run_command("git add .", cwd=workspace_path)
        if status_code != 0:
            raise RuntimeError(f"Failed to stage changes: {stderr}")

        # Get git diff
        status_code, git_diff, stderr = await self.process_manager.run_command(
            "git diff --cached || git diff",
            cwd=workspace_path,
            show_output=False,
        )
        if status_code != 0:
            raise RuntimeError(f"Failed to create initial commit: {stderr}")

        llm = self.get_llm()
        convo = AgentConvo(self).template(
            "commit",
            git_diff=git_diff,
        )
        commit_message: str = await llm(convo)

        answer = await self.ui.ask_question(
            f"Do you accept this 'git commit' message? Here is suggested message: '{commit_message}'",
            buttons={"yes": "Yes", "edit": "Edit", "no": "No, I don't want to commit changes."},
            default="yes",
            buttons_only=True,
            source=pythagora_source,
        )

        if answer.button == "no":
            return
        elif answer.button == "edit":
            user_message = await self.ui.ask_question(
                "Please enter the commit message",
                source=pythagora_source,
                initial_text=commit_message,
            )
            commit_message = user_message.text

        # Create commit
        status_code, _, stderr = await self.process_manager.run_command(
            f'git commit -m "{commit_message}"', cwd=workspace_path
        )
        if status_code != 0:
            raise RuntimeError(f"Failed to create commit: {stderr}")
