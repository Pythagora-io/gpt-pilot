import os
import shutil
import zipfile
from tempfile import TemporaryDirectory
from subprocess import check_call

# Only these top-level items will be included in the package
INCLUDE = [
    "pilot",
    "Dockerfile",
    "docker-compose.yml",
    "LICENSE",
    "README.md",
    "requirements.txt",
    "setup.py"
]

def find_repo_root() -> str:
    """
    Returns the path to the root of the repository, or None if not found.
    """
    # Find repository root
    dir = os.path.dirname(os.path.normpath(os.path.abspath(__file__)))

    # While we haven't reached the root of the filesystem...
    while dir != os.path.dirname(dir):
        if os.path.exists(os.path.join(dir, ".git")):
            break
        dir = os.path.dirname(dir)
    else:
        return None

    # Verify there's a "pilot" subdirectory in the repo root
    if not os.path.exists(os.path.join(dir, "pilot")):
        return None
    return dir


def main():
    repo_dir = find_repo_root()
    if repo_dir is None:
        print("Could not find GPT Pilot: please run me from the repository root directory.")

    os.chdir(repo_dir)

    with TemporaryDirectory() as tmp_dir:
        # Create a repository archive
        temp_archive_path = os.path.join(tmp_dir, "repository.zip")
        check_call(["git", "archive", "-o", temp_archive_path, "main"])
        check_call(["unzip", "-qq", "-x", temp_archive_path], cwd=tmp_dir)

        # Remove all items from the archive that aren't explictly whitelisted
        for item in os.listdir(tmp_dir):
            if item not in INCLUDE:
                path = os.path.join(tmp_dir, item)
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)

        archive_path = os.path.abspath(os.path.join("..", "gpt-pilot-packaged.zip"))
        if os.path.exists(archive_path):
            os.remove(archive_path)

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for dpath, dirs, files in os.walk(tmp_dir):
                for file in files:
                    full_path = os.path.join(dpath, file)
                    if full_path != temp_archive_path:
                        rel_path = os.path.relpath(full_path, tmp_dir)
                        print(rel_path)
                        zip_file.write(full_path, rel_path)

        size = os.path.getsize(archive_path)
        print(f"\nCreated: {archive_path} ({size // 1024} KB)")


if __name__ == "__main__":
    main()
