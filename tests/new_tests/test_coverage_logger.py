import logging
import sys
import unittest
from unittest.mock import MagicMock, patch

import logger_config


class TestLoggerConfig(unittest.TestCase):
    def setUp(self):
        # Reset the global flag before each test
        logger_config._LOGGING_INITIALIZED = False

    def tearDown(self):
        logger_config._LOGGING_INITIALIZED = False

    def test_setup_logging_first_run(self):
        with patch("logging.getLogger") as mock_get_logger, patch(
            "logging.handlers.RotatingFileHandler"
        ) as mock_rfh, patch("sys.stdout"), patch("pathlib.Path.mkdir"), patch(
            "pathlib.Path.home"
        ) as mock_home:

            mock_logger = MagicMock()
            mock_logger.handlers = []
            mock_get_logger.return_value = mock_logger

            mock_home.return_value = MagicMock()

            logger_config.setup_logging()

            mock_logger.setLevel.assert_called_with(logging.DEBUG)
            self.assertTrue(logger_config._LOGGING_INITIALIZED)
            self.assertTrue(mock_logger.addHandler.called)

    def test_setup_logging_already_initialized(self):
        logger_config._LOGGING_INITIALIZED = True
        with patch("logging.getLogger") as mock_get_logger:
            logger_config.setup_logging()
            mock_get_logger.assert_not_called()

    def test_setup_logging_clears_handlers(self):
        with patch("logging.getLogger") as mock_get_logger, patch(
            "logging.handlers.RotatingFileHandler"
        ), patch("pathlib.Path.mkdir"):

            mock_logger = MagicMock()
            existing_handler = MagicMock()
            # Use a real list so clear() works
            mock_logger.handlers = [existing_handler]
            mock_get_logger.return_value = mock_logger

            logger_config.setup_logging()

            # handlers list should be cleared (but new ones added)
            self.assertNotIn(existing_handler, mock_logger.handlers)

    def test_setup_logging_file_error(self):
        with patch("logging.getLogger") as mock_get_logger, patch(
            "logging.handlers.RotatingFileHandler", side_effect=Exception("Perm Error")
        ), patch("pathlib.Path.mkdir"), patch("sys.stderr") as mock_stderr:

            mock_logger = MagicMock()
            mock_logger.handlers = []
            mock_get_logger.return_value = mock_logger

            logger_config.setup_logging()
            # Should print to stderr
            pass
