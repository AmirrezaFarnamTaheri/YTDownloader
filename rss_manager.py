import requests
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

<<<<<<< HEAD
=======

>>>>>>> origin/main
class RSSManager:
    """Manages RSS feeds and checking for new videos."""

    @staticmethod
    def parse_feed(url: str) -> List[Dict[str, str]]:
        """
        Parses a YouTube RSS feed and returns a list of videos.

        Returns a list of dictionaries, where each dictionary contains:
        - title
        - link
        - published
        - video_id
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)
<<<<<<< HEAD
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}

            videos = []
            for entry in root.findall('atom:entry', ns):
                video = {}
                video['title'] = entry.find('atom:title', ns).text
                video['link'] = entry.find('atom:link', ns).attrib['href']
                video['published'] = entry.find('atom:published', ns).text
                video['video_id'] = entry.find('yt:videoId', ns).text
=======
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "yt": "http://www.youtube.com/xml/schemas/2015",
            }

            videos = []
            for entry in root.findall("atom:entry", ns):
                video = {}
                video["title"] = entry.find("atom:title", ns).text
                video["link"] = entry.find("atom:link", ns).attrib["href"]
                video["published"] = entry.find("atom:published", ns).text
                video["video_id"] = entry.find("yt:videoId", ns).text
>>>>>>> origin/main
                videos.append(video)

            return videos
        except Exception as e:
            logger.error(f"Error parsing RSS feed {url}: {e}")
            return []

    @staticmethod
    def get_latest_video(url: str) -> Optional[Dict[str, str]]:
        """Returns the latest video from the feed."""
        videos = RSSManager.parse_feed(url)
        if videos:
            return videos[0]
        return None
