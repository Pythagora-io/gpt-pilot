import os
import sys


def add_raw_tags_to_file(file_path):
    """Add {% raw %} at the beginning and {% endraw %} at the end of the file, if not already present."""
    try:
        # Open the file and read the contents
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Check if the tags are already present
        if content.startswith("{% raw %}") and content.endswith("{% endraw %}\n"):
            print(f"Skipping file (tags already added): {file_path}")
            return

        # Add {% raw %} at the beginning and {% endraw %} at the end
        modified_content = f"{'{% raw %}'}\n{content}\n{'{% endraw %}'}"

        # Write the modified content back to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(modified_content)

        print(f"Processed file: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")


def process_directory(directory):
    """Recursively process all files in the given directory."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Construct the full file path
            file_path = os.path.join(root, file)

            # Process the file
            add_raw_tags_to_file(file_path)


if __name__ == "__main__":
    # Check if the directory path argument is provided
    if len(sys.argv) != 2:
        print("Usage: python add_raw_tags.py <directory_path>")
        sys.exit(1)

    # Get the directory path from the command line argument
    directory_path = sys.argv[1]

    # Check if the provided directory exists
    if not os.path.isdir(directory_path):
        print(f"Error: The directory '{directory_path}' does not exist.")
        sys.exit(1)

    # Process the directory
    process_directory(directory_path)
