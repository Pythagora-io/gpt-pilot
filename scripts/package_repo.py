import os
import shutil
import zipfile

def main():
    # Define the base directory (one level up from /scripts)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Define paths based on base directory
    env_path = os.path.join(base_dir, "pilot", ".env")
    tmp_env_path = os.path.join("/tmp", ".env")
    repo_path = os.path.abspath(base_dir)

    # Check if .env exists
    if os.path.exists(env_path):
        # Step 1: Move .env to /tmp/x
        shutil.move(env_path, tmp_env_path)

    # Step 2: Package the repository using Python's zipfile module
    parent_directory = os.path.dirname(base_dir)
    archive_path = os.path.join(parent_directory, "gpt-pilot-packaged.zip")

    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                archive_path = os.path.relpath(file_path, repo_path)
                archive.write(file_path, archive_path)

    # Step 3: Move the .env file back, if it existed initially
    if os.path.exists(tmp_env_path):
        shutil.move(tmp_env_path, env_path)

if __name__ == "__main__":
    main()
