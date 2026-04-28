import logging
import threading

import logger_config


def test_setup_logging_is_single_initialization_under_threads(monkeypatch):
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_initialized = logger_config._logging_initialized

    calls = []

    class DummyHandler(logging.Handler):
        def emit(self, record):
            pass

    def make_handler(*args, **kwargs):
        calls.append((args, kwargs))
        return DummyHandler()

    monkeypatch.setattr(logger_config, "_logging_initialized", False)
    monkeypatch.setattr(
        logger_config.logging.handlers, "RotatingFileHandler", make_handler
    )

    try:
        threads = [threading.Thread(target=logger_config.setup_logging) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(calls) <= 2
    finally:
        root_logger.handlers[:] = original_handlers
        logger_config._logging_initialized = original_initialized
