# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
"""
Coverage tests for BatchImporter.
"""

import unittest
from unittest.mock import MagicMock, mock_open, patch

from batch_importer import BatchImporter


class TestBatchImporterCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_queue = MagicMock()
        self.mock_config = MagicMock()
        self.importer = BatchImporter(self.mock_queue, self.mock_config)

    def test_init(self):
        self.assertEqual(self.importer.queue_manager, self.mock_queue)
        self.assertEqual(self.importer.config, self.mock_config)

    @patch("batch_importer.is_safe_path")
    @patch("batch_importer.Path")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="http://url1.com\nhttp://url2.com",
    )
    def test_import_from_file_success(self, mock_file, MockPath, mock_is_safe):
        # Configure Path mock
        mock_path_obj = MockPath.return_value
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_file.return_value = True
        mock_path_obj.suffix = ".txt"
        mock_is_safe.return_value = True

        count, truncated = self.importer.import_from_file("test.txt")

        self.assertEqual(count, 2)
        self.assertFalse(truncated)
        self.assertEqual(self.mock_queue.add_item.call_count, 2)

    @patch("batch_importer.is_safe_path")
    @patch("batch_importer.Path")
    @patch(
        "builtins.open", new_callable=mock_open, read_data="invalid\nhttp://valid.com"
    )
    def test_import_from_file_mixed(self, mock_file, MockPath, mock_is_safe):
        # Configure Path mock
        mock_path_obj = MockPath.return_value
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_file.return_value = True
        mock_path_obj.suffix = ".txt"
        mock_is_safe.return_value = True

        # Logic in BatchImporter doesn't validate URLs, it just skips empty lines
        count, truncated = self.importer.import_from_file("test.txt")

        # It adds both because the simplistic check only skips empty
        self.assertEqual(count, 2)
        self.assertEqual(self.mock_queue.add_item.call_count, 2)

    @patch("batch_importer.Path")
    def test_import_from_file_not_found(self, MockPath):
        mock_path_obj = MockPath.return_value
        mock_path_obj.exists.return_value = False

        with self.assertRaises(ValueError):
            self.importer.import_from_file("missing.txt")

    @patch("batch_importer.is_safe_path")
    @patch("batch_importer.Path")
    @patch("builtins.open", new_callable=mock_open)
    def test_import_from_file_limit(self, mock_file, MockPath, mock_is_safe):
        # Configure Path mock
        mock_path_obj = MockPath.return_value
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_file.return_value = True
        mock_path_obj.suffix = ".txt"
        mock_is_safe.return_value = True

        # Generate 105 URLs
        data = "\n".join([f"http://url{i}.com" for i in range(105)])

        # If we use mock_open(read_data=data), it should handle iteration automatically
        # But since we passed mock_open as new_callable, we need to configure it correctly
        # Let's try configuring side_effect for the file handle's __iter__
        mock_file.return_value.__iter__.side_effect = lambda: iter(data.splitlines())

        count, truncated = self.importer.import_from_file("test.txt")

        self.assertEqual(count, 100)
        self.assertTrue(truncated)
        self.assertEqual(self.mock_queue.add_item.call_count, 100)

    @patch("batch_importer.is_safe_path")
    @patch("batch_importer.Path")
    @patch("builtins.open", new_callable=mock_open, read_data="http://test.com")
    def test_import_queue_full(self, mock_file, MockPath, mock_is_safe):
        # Configure Path mock
        mock_path_obj = MockPath.return_value
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_file.return_value = True
        mock_path_obj.suffix = ".txt"
        mock_is_safe.return_value = True

        # If add_item raises exception, it bubbles up, is caught, logged, AND RE-RAISED.
        # Code: raise ex
        self.mock_queue.add_item.side_effect = ValueError("Queue is full")

        with self.assertRaises(ValueError):
            self.importer.import_from_file("test.txt")
