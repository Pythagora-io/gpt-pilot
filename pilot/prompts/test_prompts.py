from .prompts import get_prompt


def test_prompt_ran_command_None_exit():
    # When
    prompt = get_prompt('dev_ops/ran_command.prompt', {
        'cli_response': 'stdout:\n```\nsuccess\n```',
        'command': './scripts/run_tests',
        'additional_message': 'Some additional message\n',
        'exit_code': None
    })

    # Then
    assert prompt == '''
I ran the command `./scripts/run_tests`. The output was:

stdout:
```
success
```

If the command was successfully executed, respond with `DONE`. If it wasn't, respond with `NEEDS_DEBUGGING`.
'''.strip()


def test_prompt_ran_command_0_exit():
    # When
    prompt = get_prompt('dev_ops/ran_command.prompt', {
        'cli_response': 'stdout:\n```\nsuccess\n```',
        'command': './scripts/run_tests',
        'additional_message': 'Some additional message\n',
        'exit_code': 0
    })

    # Then
    assert prompt == '''
I ran the command `./scripts/run_tests`, the exit code was 0. The output was:

stdout:
```
success
```

If the command was successfully executed, respond with `DONE`. If it wasn't, respond with `NEEDS_DEBUGGING`.
'''.strip()


def test_parse_task_no_processes():
    # When
    prompt = get_prompt('development/parse_task.prompt', {
        'running_processes': {}
    })

    # Then
    assert 'the following processes' not in prompt


def test_parse_task_with_processes():
    # When
    prompt = get_prompt('development/parse_task.prompt', {
        'running_processes': {
            'app': ('npm start', 123),
            'mongo': ('mongod', 456)
        }
    })

    # Then
    assert 'the following processes are already running:' in prompt
    assert 'command_id: app\ncommand: npm start\n\ncommand_id: mongo\ncommand: mongod' in prompt
