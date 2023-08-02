from termcolor import colored


def update_file(path, new_content):
    with open(path, 'w') as file:
        file.write(new_content)
        print(colored(f"Updated file {path}", "green"))
