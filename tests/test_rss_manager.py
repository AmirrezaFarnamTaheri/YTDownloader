# pylint: disable=line-too-long, wrong-import-position, too-many-instance-attributes, too-many-public-methods, invalid-name, unused-variable, import-outside-toplevel
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, too-many-positional-arguments, unused-argument, unused-import, protected-access
import unittest
from unittest.mock import MagicMock, patch

from rss_manager import RSSManager


class TestRSSManager(unittest.TestCase):

    @patch("rss_manager.validate_url", return_value=True)
    @patch("rss_manager.safe_request_with_redirects")
    def test_parse_feed_success(self, mock_request, _mock_validate):
        # Mock XML response. Note: Ensure namespaces are correct for ElementTree default parsing
        # The parser logic in RSSManager uses {http://www.w3.org/2005/Atom} tags
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
            <entry>
                <id>yt:video:VIDEO_ID</id>
                <yt:videoId>VIDEO_ID</yt:videoId>
                <yt:channelId>CHANNEL_ID</yt:channelId>
                <title>Test Video</title>
                <link rel="alternate" href="https://www.youtube.com/watch?v=VIDEO_ID"/>
                <published>2023-10-27T10:00:00+00:00</published>
            </entry>
        </feed>
        """
        mock_response = MagicMock()
        # RSSManager now uses response.text, not response.content
        mock_response.text = xml_content
        # Set apparent_encoding
        mock_response.apparent_encoding = "utf-8"
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {}
        mock_request.return_value = mock_response

        videos = RSSManager.parse_feed("http://fake.url")
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["title"], "Test Video")
        self.assertEqual(videos[0]["video_id"], "VIDEO_ID")
        self.assertEqual(videos[0]["link"], "https://www.youtube.com/watch?v=VIDEO_ID")

    @patch("rss_manager.validate_url", return_value=True)
    @patch("rss_manager.safe_request_with_redirects")
    def test_parse_feed_error(self, mock_request, _mock_validate):
        mock_request.side_effect = Exception("Network error")
        videos = RSSManager.parse_feed("http://fake.url")
        self.assertEqual(videos, [])

    @patch("rss_manager.validate_url", return_value=True)
    @patch("rss_manager.safe_request_with_redirects")
    def test_parse_feed_rejects_oversized_content_length(
        self, mock_request, _mock_validate
    ):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": str(6 * 1024 * 1024)}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        self.assertEqual(RSSManager.parse_feed("http://fake.url"), [])

    @patch("rss_manager.RSSManager.parse_feed")
    def test_get_latest_video(self, mock_parse):
        mock_parse.return_value = [{"title": "Latest", "link": "http://link"}]
        video = RSSManager.get_latest_video("http://fake.url")
        # pylint: disable=unsubscriptable-object
        self.assertEqual(video["title"], "Latest")

    @patch("rss_manager.RSSManager.parse_feed")
    def test_get_latest_video_none(self, mock_parse):
        mock_parse.return_value = []
        video = RSSManager.get_latest_video("http://fake.url")
        self.assertIsNone(video)
