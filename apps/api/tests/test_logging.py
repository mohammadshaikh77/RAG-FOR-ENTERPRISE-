from apps.api.src.logging import get_logger, setup_logging


def test_logging_setup() -> None:
    setup_logging(log_level="DEBUG", environment="development")
    logger = get_logger("test.logger")
    assert logger is not None
    # Verify logger doesn't raise exception when logging
    logger.info("Test logging message", key="value")
