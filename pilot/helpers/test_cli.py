from pilot.helpers.cli import terminate_process


def test_terminate_process_not_running():
    terminate_process(999999999, 'not running')
    assert True
