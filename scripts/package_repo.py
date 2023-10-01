import os
import shutil
import zipfile

def main():
    # Define the base directory (one level up from /scripts)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_path = os.path.abspath(base_dir)

    # Files to exclude from the repo temporarily while packaging
    files_to_exclude = [
        "pilot/.env",
        "pilot/gpt-pilot"
    ]

    # Step 1: Move excluded files to /tmp
    tmp_excluded_paths = []
    for file in files_to_exclude:
        source_path = os.path.join(repo_path, file)
        if os.path.exists(source_path):
            tmp_path = os.path.join("/tmp", os.path.basename(file))
            shutil.move(source_path, tmp_path)
            tmp_excluded_paths.append((tmp_path, source_path))

    # Items to package
    items_to_package = [
        "pilot",
        "scripts",
        "Dockerfile",
        "docker-compose.yml",
        "LICENSE",
        "README.md",
        "requirements.txt"
    ]

    # Step 2: Package the specified items using Python's zipfile module
    parent_directory = os.path.dirname(base_dir)
    archive_path = os.path.join(parent_directory, "gpt-pilot-packaged.zip")

    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in items_to_package:
            item_path = os.path.join(repo_path, item)
            if os.path.isfile(item_path):
                archive.write(item_path, item)
            elif os.path.isdir(item_path):
                for root, _, files in os.walk(item_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        archive_path = os.path.relpath(file_path, repo_path)
                        archive.write(file_path, archive_path)

    # Step 3: Move the excluded files back
    for tmp_path, orig_path in tmp_excluded_paths:
        if os.path.exists(tmp_path):
            shutil.move(tmp_path, orig_path)

if __name__ == "__main__":
    main()
