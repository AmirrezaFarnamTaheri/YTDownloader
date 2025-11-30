import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


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
            logger.debug(f"Fetching RSS feed: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "yt": "http://www.youtube.com/xml/schemas/2015",
            }

            videos = []
            entries = root.findall("atom:entry", ns)
            logger.debug(f"Found {len(entries)} entries in feed")

            for entry in entries:
                video = {}
                try:
                    video["title"] = entry.find("atom:title", ns).text
                    video["link"] = entry.find("atom:link", ns).attrib["href"]
                    video["published"] = entry.find("atom:published", ns).text
                    video["video_id"] = entry.find("yt:videoId", ns).text
                    videos.append(video)
                except AttributeError as e:
                    logger.warning(f"Skipping malformed RSS entry in {url}: {e}")
                    continue

            logger.info(f"Successfully parsed {len(videos)} videos from feed: {url}")
            return videos
        except requests.RequestException as e:
            logger.error(f"Network error fetching RSS feed {url}: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"XML parsing error for feed {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing RSS feed {url}: {e}", exc_info=True)
            return []

    @staticmethod
    def get_latest_video(url: str) -> Optional[Dict[str, str]]:
        """Returns the latest video from the feed."""
        videos = RSSManager.parse_feed(url)
        if videos:
            return videos[0]
        return None
