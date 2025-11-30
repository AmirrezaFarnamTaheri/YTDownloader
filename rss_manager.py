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
                video: Dict[str, str] = {}
                try:
                    title_elem = entry.find("atom:title", ns)
                    link_elem = entry.find("atom:link", ns)
                    pub_elem = entry.find("atom:published", ns)
                    vid_elem = entry.find("yt:videoId", ns)

                    if (
                        title_elem is not None
                        and title_elem.text
                        and link_elem is not None
                        and pub_elem is not None
                        and pub_elem.text
                        and vid_elem is not None
                        and vid_elem.text
                    ):
                        video["title"] = title_elem.text
                        # attrib is a dict, but mypy might worry. link_elem is not None here.
                        # .attrib is usually present on Element.
                        href = link_elem.attrib.get("href")
                        if href:
                            video["link"] = href
                        else:
                            continue
                        video["published"] = pub_elem.text
                        video["video_id"] = vid_elem.text
                        videos.append(video)
                except AttributeError as e:
                    logger.warning(f"Skipping malformed RSS entry in {url}: {e}")
                    continue

            logger.info(f"Successfully parsed {len(videos)} videos from feed: {url}")
            return videos
        except requests.RequestException as e:
            logger.error(f"Network error fetching RSS feed {url}: {e}", exc_info=True)
            return []
        except ET.ParseError as e:
            logger.error(f"XML parsing error for feed {url}: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing RSS feed {url}: {e}", exc_info=True)
            return []

    @staticmethod
    def get_latest_video(url: str) -> Optional[Dict[str, str]]:
        """Returns the latest video from the feed."""
        logger.debug(f"Getting latest video from {url}")
        videos = RSSManager.parse_feed(url)
        if videos:
            logger.debug(f"Latest video: {videos[0].get('title', 'Unknown')}")
            return videos[0]
        logger.debug("No videos found in feed.")
        return None
