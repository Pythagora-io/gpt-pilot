from os.path import join

from core.config import LogConfig
from core.log import get_logger, setup


def test_file_handler(tmp_path):
    output = join(tmp_path, "test.log")
    cfg = LogConfig(level="DEBUG", output=output)
    setup(cfg, force=True)

    logger = get_logger("core")
    logger.debug("debug message")

    assert len(logger.handlers) == 1
    handler = logger.handlers[0]
    assert handler.level == 10
    assert handler.stream.name == output

    logger.removeHandler(handler)
    handler.close()


def test_log_level(capsys):
    cfg = LogConfig(level="WARNING", output=None)
    setup(cfg, force=True)

    logger = get_logger("core.test_default_setup")
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")

    stderr = capsys.readouterr().err
    assert "debug message" not in stderr
    assert "info message" not in stderr
    assert "warning message" in stderr
    assert "error message" in stderr
    assert "critical message" in stderr
