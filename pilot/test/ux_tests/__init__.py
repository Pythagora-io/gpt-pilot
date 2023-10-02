from .run_command_until_success import run_command_until_success


def run_test(test_name: str):
    print(f'Running UX test "{test_name}"...')

    if test_name == 'run_command_until_success':
        return run_command_until_success()

    print(f'UX test "{test_name}" not found')
