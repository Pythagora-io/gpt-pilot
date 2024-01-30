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
Some additional message

I ran the command `./scripts/run_tests`. The output was:

stdout:
```
success
```

Think about this output and not any output in previous messages. If the command was successfully executed, respond with `DONE`. If it wasn't, respond with `BUG`.

Do not respond with anything other than these two keywords.
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
Some additional message

I ran the command `./scripts/run_tests`. The output was:

stdout:
```
success
```

Think about this output and not any output in previous messages. If the command was successfully executed, respond with `DONE`. If it wasn't, respond with `BUG`.

Do not respond with anything other than these two keywords.
'''.strip()


def test_parse_task_no_processes():
    # When
    prompt = get_prompt('development/parse_task.prompt', {
        'running_processes': {}
    })

    # Then
    assert 'the following processes' not in prompt
