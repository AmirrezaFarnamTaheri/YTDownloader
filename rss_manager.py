"""
RSS Manager module for fetching and parsing RSS feeds.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class RSSManager:
    """Manages RSS feed subscriptions and updates."""

    def __init__(self, config_manager):
        self.config = config_manager
        self.feeds = self.config.get("rss_feeds", [])

    def get_feeds(self) -> List[Dict[str, str]]:
        """Return list of feeds."""
        return self.feeds

    def add_feed(self, url: str):
        """Add a new RSS feed."""
        if not any(f["url"] == url for f in self.feeds):
            self.feeds.append({"url": url, "name": url})  # Name will be updated later
            self.config.set("rss_feeds", self.feeds)
            logger.info("Added RSS feed: %s", url)

    def remove_feed(self, url: str):
        """Remove an RSS feed."""
        self.feeds = [f for f in self.feeds if f["url"] != url]
        self.config.set("rss_feeds", self.feeds)
        logger.info("Removed RSS feed: %s", url)

    def fetch_feed(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed (Instance wrapper)."""
        return RSSManager.parse_feed(url, self)

    @staticmethod
    def parse_feed(
        url: str, instance: Optional["RSSManager"] = None
    ) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed (Static implementation)."""
        try:
            logger.debug("Fetching RSS feed: %s", url)
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            items = []
            # Handle Atom vs RSS
            if "feed" in root.tag:
                RSSManager._parse_atom_feed(root, items, instance, url)
            else:
                RSSManager._parse_rss_feed(root, items, instance, url)

            logger.info("Fetched %d items from %s", len(items), url)
            return items

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to fetch RSS feed %s: %s", url, e)
            return []

    @staticmethod
    def _parse_atom_feed(
        root: ET.Element,
        items: List[Dict[str, Any]],
        instance: Optional["RSSManager"],
        url: str,
    ):
        """Parse Atom feed entries."""
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        # Update feed title if needed
        title_elem = root.find("atom:title", ns)
        if instance and title_elem is not None and title_elem.text:
            # pylint: disable=protected-access
            instance._update_feed_name(url, title_elem.text)

        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            link = entry.find("atom:link", ns)
            published = entry.find("atom:published", ns)
            if published is None:
                published = entry.find("atom:updated", ns)
            video_id_elem = entry.find("yt:videoId", ns)

            link_href = link.attrib.get("href") if link is not None else None

            if title is not None and title.text and link_href:
                item_data = {
                    "title": title.text,
                    "link": link_href,
                    "published": (published.text if published is not None else None),
                }
                if video_id_elem is not None:
                    item_data["video_id"] = video_id_elem.text
                items.append(item_data)

    @staticmethod
    def _parse_rss_feed(
        root: ET.Element,
        items: List[Dict[str, Any]],
        instance: Optional["RSSManager"],
        url: str,
    ):
        """Parse RSS 2.0 feed items."""
        channel = root.find("channel")
        if channel is not None:
            title_elem = channel.find("title")
            if instance and title_elem is not None and title_elem.text:
                # pylint: disable=protected-access
                instance._update_feed_name(url, title_elem.text)

            for item in channel.findall("item"):
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")

                if title is not None and title.text and link is not None and link.text:
                    items.append(
                        {
                            "title": title.text,
                            "link": link.text,
                            "published": (
                                pub_date.text if pub_date is not None else None
                            ),
                        }
                    )

    def _update_feed_name(self, url: str, name: str):
        """Update the friendly name of a feed."""
        for feed in self.feeds:
            if feed["url"] == url and feed["name"] == url:
                feed["name"] = name
                self.config.set("rss_feeds", self.feeds)
                logger.debug("Updated feed name for %s to %s", url, name)
                break

    def get_aggregated_items(self) -> List[Dict[str, Any]]:
        """Fetch all feeds and return combined, sorted items."""
        all_items = []
        for feed in self.feeds:
            # Normalize feed entry
            if isinstance(feed, str):
                url = feed
                name = feed
            else:
                url = feed.get("url")
                name = feed.get("name", url)

            if not url:
                continue

            try:
                items = self.fetch_feed(url)
            except Exception as e:
                logger.error("Failed to fetch feed %s: %s", url, e)
                continue

            for item in items:
                item["feed_name"] = name
                # Try to parse date for sorting
                try:
                    if item.get("published"):
                        item["date_obj"] = date_parser.parse(item["published"])
                    else:
                        item["date_obj"] = datetime.min
                except Exception:  # pylint: disable=broad-exception-caught
                    item["date_obj"] = datetime.min
                all_items.append(item)

        # Sort by date descending
        all_items.sort(key=lambda x: x["date_obj"], reverse=True)
        return all_items

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Alias for get_aggregated_items to match test/view usage."""
        return self.get_aggregated_items()

    @classmethod
    def get_latest_video(cls, url: str) -> Optional[Dict[str, Any]]:
        """Get the latest video from a feed (Static)."""
        items = cls.parse_feed(url)
        if items:
            return items[0]
        return None
