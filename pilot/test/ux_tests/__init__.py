# from .run_command_until_success import run_command_until_success
from .cli_execute_command import cli_execute_command
from .Dev_continue_development import test_continue_development
from .utils import use_args


def run_test(test_name: str, args):
    print(f'Running UX test "{test_name}"...')

    tests = {
        # 'run_command_until_success': run_command_until_success,
        'cli_execute_command': cli_execute_command,
        'continue_development': test_continue_development,
    }

    if test_name in tests:
        use_args(args)
        return tests[test_name]()

    print(f'UX test "{test_name}" not found')
