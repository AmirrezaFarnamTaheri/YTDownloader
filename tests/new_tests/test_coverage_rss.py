import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rss_manager import RSSManager


class TestRSSManager(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_config.get.return_value = []
        self.manager = RSSManager(self.mock_config)

    @patch("config_manager.ConfigManager")
    def test_add_feed(self, MockConfig):
        self.manager.add_feed("http://feed.com")
        MockConfig.save_config.assert_called()
        self.assertEqual(len(self.manager.feeds), 1)
        self.assertEqual(self.manager.feeds[0]["url"], "http://feed.com")

    @patch("config_manager.ConfigManager")
    def test_remove_feed(self, MockConfig):
        self.manager.feeds = [{"url": "http://feed.com", "name": "Test"}]
        self.manager.remove_feed("http://feed.com")
        MockConfig.save_config.assert_called()
        self.assertEqual(len(self.manager.feeds), 0)

    @patch("rss_manager.requests.get")
    def test_parse_feed_success(self, mock_get):
        # Mock requests.get response
        mock_response = MagicMock()
        mock_response.text = """
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Test Feed</title>
            <entry>
                <title>Video Title</title>
                <link href="http://video.com"/>
                <published>2023-01-01T00:00:00Z</published>
            </entry>
        </feed>
        """
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        items = self.manager.parse_feed("http://feed.com")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Video Title")

    @patch("rss_manager.requests.get")
    def test_parse_feed_error(self, mock_get):
        mock_get.side_effect = Exception("Network Error")
        items = self.manager.parse_feed("http://feed.com")
        self.assertEqual(items, [])
