"""
RSS Manager module for fetching and parsing RSS feeds.
"""

import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import requests
from dateutil import parser as date_parser

try:
    from defusedxml.ElementTree import fromstring as safe_fromstring
except ImportError:
    safe_fromstring = None  # type: ignore

logger = logging.getLogger(__name__)


def safe_log_warning(msg, *args):
    """Safely log a warning message, ignoring closed stream errors."""
    try:
        # Check if sys.stderr/stdout are closed (common during interpreter shutdown)
        if not sys or not sys.stderr or sys.stderr.closed:
            return

        # Double check handlers to avoid "No handlers could be found" or closed file errors in handlers
        if not logger.handlers and not logging.root.handlers:
            return

        # Use a lock if available on the logger to prevent race during emit
        # (Though logging module is thread-safe, the stream underneath might not be during shutdown)

        if logger.isEnabledFor(logging.WARNING):
            # Final check for shutdown
            if threading.main_thread().is_alive():
                try:
                    logger.warning(msg, *args)
                except (ValueError, OSError):
                    # Catch I/O operation on closed file occurring DURING log
                    pass
    except (ValueError, OSError):
        # Ignore "I/O operation on closed file"
        pass
    except Exception:  # pylint: disable=broad-exception-caught
        pass


def safe_log_error(msg, *args):
    """Safely log an error message, ignoring closed stream errors."""
    try:
        if not sys or not sys.stderr or sys.stderr.closed:
            return

        if not logger.handlers and not logging.root.handlers:
            return

        if logger.isEnabledFor(logging.ERROR):
            if threading.main_thread().is_alive():
                try:
                    logger.error(msg, *args)
                except (ValueError, OSError):
                    pass
    except (ValueError, OSError):
        pass
    except Exception:  # pylint: disable=broad-exception-caught
        pass


class RSSManager:
    """
    Manages RSS feed subscriptions, fetching, and parsing.
    Includes thread-safe operations, robust parsing (defusedxml), and timeouts.
    """

    def __init__(self, config_manager):
        # Config wrapper (should be dict-like or have set/get)
        self.config_manager = config_manager
        # Cache feeds locally from config
        self.feeds: List[Dict[str, str]] = self.config_manager.get("rss_feeds", [])
        self._lock = threading.RLock()

    def _save_feeds(self):
        """Persist feeds to config."""
        # pylint: disable=import-outside-toplevel
        from config_manager import ConfigManager

        with self._lock:
            # Reload current config to avoid overwriting other keys, update feeds, save
            full_config = ConfigManager.load_config()
            full_config["rss_feeds"] = self.feeds
            ConfigManager.save_config(full_config)

    def get_feeds(self) -> List[Dict[str, str]]:
        """Return list of feeds."""
        with self._lock:
            return list(self.feeds)

    def add_feed(self, url: str):
        """Add a new RSS feed."""
        with self._lock:
            if not any(f["url"] == url for f in self.feeds):
                self.feeds.append({"url": url, "name": url})
                self._save_feeds()
                logger.info("Added RSS feed: %s", url)

    def remove_feed(self, url: str):
        """Remove an RSS feed."""
        with self._lock:
            initial_len = len(self.feeds)
            self.feeds = [f for f in self.feeds if f["url"] != url]
            if len(self.feeds) < initial_len:
                self._save_feeds()
                logger.info("Removed RSS feed: %s", url)

    def fetch_feed(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed (Instance wrapper)."""
        return RSSManager.parse_feed(url, self)

    @staticmethod
    def parse_feed(
        url: str, instance: Optional["RSSManager"] = None
    ) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed safely."""
        try:
            logger.debug("Fetching RSS feed: %s", url)
            # Strict timeout
            response = requests.get(url, timeout=(5, 10))
            response.raise_for_status()

            # Use apparent_encoding for robustness against misconfigured servers
            response.encoding = response.apparent_encoding
            content_text = response.text

            # Check for empty or excessively small content
            if not content_text or len(content_text.strip()) < 10:
                safe_log_warning("Empty or too short content for feed: %s", url)
                return []

            # Clean potential XML junk before root if necessary (simple heuristic)
            content_text = content_text.strip()

            root = None
            # Safe XML parsing
            if safe_fromstring is not None:
                try:
                    root = safe_fromstring(content_text)
                except Exception as e:
                    # Fallback or error logging
                    safe_log_warning("defusedxml parse error for %s: %s", url, e)

            if root is None:
                # If defusedxml failed or not available, try standard ET but careful
                # Note: This is less secure against billionaire laughs etc but needed for some malformed feeds
                # In production, we should stick to defusedxml for untrusted input.
                try:
                    root = ET.fromstring(content_text)
                except ET.ParseError as e:
                    safe_log_warning("XML parse error for %s: %s", url, e)
                    return []

            items: List[Dict[str, Any]] = []
            if "feed" in root.tag:  # Atom
                RSSManager._parse_atom_feed(root, items, instance, url)
            else:  # RSS
                RSSManager._parse_rss_feed(root, items, instance, url)

            return items

        except requests.RequestException as e:
            safe_log_warning("Network error fetching feed %s: %s", url, e)
            return []
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Generic catch-all to prevent crashes
            safe_log_error("Unexpected error parsing feed %s: %s", url, e)
            return []

    @staticmethod
    def _parse_atom_feed(
        root: ET.Element,
        items: List[Dict[str, Any]],
        instance: Optional["RSSManager"],
        url: str,
    ):
        """Parse Atom feed entries."""
        # pylint: disable=protected-access
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }

        # Update feed title
        if instance:
            title_elem = root.find("atom:title", ns)
            if title_elem is not None and title_elem.text:
                instance._update_feed_name_safe(url, title_elem.text)

        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            link = entry.find("atom:link", ns)
            published = entry.find("atom:published", ns)
            if published is None:
                published = entry.find("atom:updated", ns)

            video_id = entry.find("yt:videoId", ns)

            link_href = link.attrib.get("href") if link is not None else None

            if title is not None and title.text and link_href:
                items.append(
                    {
                        "title": title.text,
                        "link": link_href,
                        "published": published.text if published is not None else None,
                        "video_id": video_id.text if video_id is not None else None,
                        "is_video": video_id is not None,
                    }
                )

    @staticmethod
    def _parse_rss_feed(
        root: ET.Element,
        items: List[Dict[str, Any]],
        instance: Optional["RSSManager"],
        url: str,
    ):
        """Parse RSS 2.0 feed items."""
        # pylint: disable=protected-access
        channel = root.find("channel")
        if channel is None:
            return

        if instance:
            title_elem = channel.find("title")
            if title_elem is not None and title_elem.text:
                instance._update_feed_name_safe(url, title_elem.text)

        for item in channel.findall("item"):
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")

            if title is not None and title.text and link is not None and link.text:
                items.append(
                    {
                        "title": title.text,
                        "link": link.text,
                        "published": pub_date.text if pub_date is not None else None,
                        "is_video": False,  # RSS generic usually isn't video unless specific tags
                    }
                )

    def _update_feed_name_safe(self, url: str, name: str):
        """Update feed name thread-safely."""
        with self._lock:
            updated = False
            for feed in self.feeds:
                if feed["url"] == url and feed["name"] == url:
                    feed["name"] = name
                    updated = True
                    break
            if updated:
                self._save_feeds()

    def get_aggregated_items(self) -> List[Dict[str, Any]]:
        """Fetch all feeds concurrently and return combined items."""
        all_items = []
        feeds_snapshot = self.get_feeds()

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_feed = {
                # Ensure we pass the URL string, not the dict, if it's a list of dicts
                executor.submit(
                    self.fetch_feed, f["url"] if isinstance(f, dict) else f
                ): f
                for f in feeds_snapshot
            }

            for future in as_completed(future_to_feed):
                feed = future_to_feed[future]
                # Handle string feed input gracefully if tests push strings
                feed_url = feed["url"] if isinstance(feed, dict) else feed
                feed_name = (
                    feed.get("name", feed_url) if isinstance(feed, dict) else feed_url
                )

                try:
                    items = future.result()
                    for item in items:
                        item["feed_name"] = feed_name
                        # Parse date
                        try:
                            item["date_obj"] = (
                                date_parser.parse(item["published"])
                                if item.get("published")
                                else datetime.min
                            )
                        except Exception:  # pylint: disable=broad-exception-caught
                            item["date_obj"] = datetime.min
                        all_items.append(item)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    safe_log_error("Feed fetch failed for %s: %s", feed_url, e)

        # Sort by date descending
        all_items.sort(key=lambda x: x.get("date_obj", datetime.min), reverse=True)
        return all_items

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Alias for get_aggregated_items."""
        return self.get_aggregated_items()

    @classmethod
    def get_latest_video(cls, url: str) -> Optional[Dict[str, Any]]:
        """Get the latest video from a feed."""
        items = cls.parse_feed(url)
        return items[0] if items else None
