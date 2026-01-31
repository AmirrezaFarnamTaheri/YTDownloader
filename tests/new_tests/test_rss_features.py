"""
Tests for RSS Features including OPML.
"""

import unittest
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree as ET

from rss_manager import RSSManager


class TestRSSFeatures(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_config.get.return_value = []
        self.manager = RSSManager(self.mock_config)

    @patch("rss_manager.safe_fromstring")
    def test_import_opml_success(self, mock_parse):
        # Mock XML structure
        root = MagicMock()
        outline1 = MagicMock()
        outline1.attrib = {"xmlUrl": "http://feed1.com", "title": "Feed 1"}
        outline2 = MagicMock()
        outline2.attrib = {"xmlUrl": "http://feed2.com", "text": "Feed 2"}

        root.findall.return_value = [outline1, outline2]
        mock_parse.return_value = root

        count = self.manager.import_opml("dummy content")

        self.assertEqual(count, 2)
        feeds = self.manager.get_feeds()
        self.assertEqual(len(feeds), 2)
        self.assertEqual(feeds[0]["url"], "http://feed1.com")
        self.assertEqual(feeds[0]["name"], "Feed 1")
        self.assertEqual(feeds[1]["url"], "http://feed2.com")
        self.assertEqual(feeds[1]["name"], "Feed 2")

    @patch("rss_manager.safe_fromstring")
    def test_import_opml_duplicates(self, mock_parse):
        # Pre-populate
        self.manager.feeds = [{"url": "http://feed1.com", "name": "Existing"}]

        root = MagicMock()
        outline1 = MagicMock()
        outline1.attrib = {"xmlUrl": "http://feed1.com", "title": "Feed 1"}

        root.findall.return_value = [outline1]
        mock_parse.return_value = root

        count = self.manager.import_opml("dummy")
        self.assertEqual(count, 0)
        self.assertEqual(len(self.manager.get_feeds()), 1)

    def test_export_opml(self):
        self.manager.feeds = [
            {"url": "http://feed1.com", "name": "Feed & Name"}
        ]

        opml = self.manager.export_opml()

        self.assertIn('xmlUrl="http://feed1.com"', opml)
        self.assertIn('text="Feed &amp; Name"', opml)
        self.assertIn('<opml version="2.0">', opml)

if __name__ == "__main__":
    unittest.main()
