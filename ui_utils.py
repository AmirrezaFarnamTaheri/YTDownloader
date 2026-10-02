"""
Utilities for UI components and platform interaction.
Includes robust validation and secure operations.
"""

# pylint: disable=too-many-return-statements

import asyncio
import inspect
import ipaddress
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urljoin, urlparse

import flet as ft
import requests

logger = logging.getLogger(__name__)


# (connect timeout, read timeout) applied to every outbound HTTP request
# that does not supply its own.
DEFAULT_HTTP_TIMEOUT = (10, 30)


# pylint: disable=too-few-public-methods
class UIConstants:
    """Class to hold UI-related constants."""

    THUMBNAIL_SIZE = (160, 120)
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 750
    QUEUE_POLL_INTERVAL = 100
    PAUSE_SLEEP_INTERVAL = 0.5
    DEFAULT_PADDING = 10
    BUTTON_PADDING = 8
    ENTRY_PADDING = 5


def safe_update(control: ft.Control) -> bool:
    """Push ``control`` to the client only when it is currently mounted.

    Flet's ``Control.update()`` raises ``AssertionError: Control must be added
    to the page first`` for controls that are not part of a page. Views are
    rebuilt and refreshed from background timers while the user may have
    navigated elsewhere, so a refresh can legitimately target a detached
    control; such updates must be skipped instead of aborting the refresh.

    Returns ``True`` when an update command was issued.
    """
    try:
        if control.page:
            control.update()
            return True
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug(
            "Skipped update for detached control %s: %s", type(control).__name__, exc
        )
    return False


def format_file_size(size_bytes: float | str | int | None) -> str:
    """Format file size for display."""
    if size_bytes is None or size_bytes == "N/A":
        return "N/A"
    try:
        size = float(size_bytes)
        if size <= 0:
            return "0.00 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
    except (ValueError, TypeError):
        return "N/A"


def _ip_is_safe(value: str) -> bool:
    """Return True when the IP literal is safe to connect to from a desktop app.

    Blocks loopback, link-local, multicast, unspecified, reserved, and
    private/RFC1918/ULA addresses to protect against SSRF-style abuse.
    """
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _host_is_public(hostname: str, resolve_host: bool = False) -> bool:
    """Return whether a hostname/IP is a public (non-local, non-private) address."""
    host = hostname.strip().strip(".").lower()
    if not host:
        return False

    if host in ("localhost", "127.0.0.1", "::1"):
        return False

    try:
        return _ip_is_safe(host)
    except ValueError:
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
            return False

    labels = host.split(".")
    if len(host) > 253 or len(labels) < 2:
        return False

    label_re = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
    if any(not label_re.match(label) for label in labels):
        return False

    if resolve_host:
        try:
            addr_infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except OSError:
            return False
        if not addr_infos:
            return False
        for info in addr_infos:
            addr = str(info[4][0])
            try:
                if not _ip_is_safe(addr):
                    return False
            except ValueError:
                return False

    return True


def validate_url(url: str, *, resolve_host: bool = False) -> bool:
    """
    Validate if URL is a valid http/https URL.
    Also implements strict SSRF protection by blocking private, loopback, link-local,
    and multicast addresses.
    """
    if not isinstance(url, str):
        return False

    url = url.strip()
    if len(url) < 8 or len(url) > 2048:
        return False

    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        return False

    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        if not parsed.netloc or not parsed.hostname:
            return False
        if parsed.username or parsed.password:
            return False
        # Accessing .port raises ValueError for invalid ports.
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return False

        hostname = parsed.hostname
        if not _host_is_public(hostname, resolve_host=resolve_host):
            return False
    except Exception:  # pylint: disable=broad-exception-caught
        return False

    return True


_YTSEARCH_RE = re.compile(r"^ytsearch(?P<count>\d{0,2}):(?P<query>.+)$", re.I)


def validate_search_target(value: str) -> bool:
    """Validate a yt-dlp search pseudo-URL such as ytsearch1:lofi beats."""
    if not isinstance(value, str):
        return False
    value = value.strip()
    match = _YTSEARCH_RE.match(value)
    if not match:
        return False

    count_text = match.group("count")
    if count_text:
        count = int(count_text)
        if count < 1 or count > 50:
            return False

    query = match.group("query").strip()
    if not query or len(query) > 512:
        return False
    return not any(ord(ch) < 32 for ch in query)


def normalize_download_target(value: str) -> str | None:
    """
    Normalize URL/search input for yt-dlp.

    Real HTTP(S) URLs are returned as-is. Existing ytsearch pseudo-URLs are
    preserved after validation. Plain text becomes a single-result yt-dlp search.
    """
    if not isinstance(value, str):
        return None

    target = value.strip()
    if validate_url(target) or validate_search_target(target):
        return target
    if target.lower().startswith("ytsearch"):
        return None

    # Inputs that look like explicit URLs with unsupported schemes should fail
    # instead of silently becoming search queries.
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target):
        return None

    if not target or len(target) > 512:
        return None
    if any(ord(ch) < 32 for ch in target):
        return None

    return f"ytsearch1:{target}"


def validate_download_target(value: str) -> bool:
    """Validate user download input, allowing either safe URLs or yt-dlp search."""
    return normalize_download_target(value) is not None


def safe_request_with_redirects(
    method: str,
    url: str,
    *,
    max_redirects: int = 5,
    **kwargs,
) -> requests.Response:
    """
    Issue an HTTP request while validating every redirect target.

    requests' built-in redirect handling resolves the next URL after the first
    outbound request has already been made. This helper checks the initial
    target and each Location header with DNS-aware URL validation before making
    the next hop.
    """
    if max_redirects < 0:
        raise ValueError("max_redirects must be non-negative")

    # Never allow an unbounded wait: a hung remote must not hang the app.
    timeout = kwargs.pop("timeout", DEFAULT_HTTP_TIMEOUT)

    current_url = url
    for _ in range(max_redirects + 1):
        if not validate_url(current_url, resolve_host=True):
            raise ValueError(f"Unsafe URL blocked: {current_url}")

        response = requests.request(
            method,
            current_url,
            allow_redirects=False,
            timeout=timeout,
            **kwargs,
        )
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise requests.TooManyRedirects("Redirect response missing Location")
            current_url = urljoin(current_url, location)
            continue
        return response

    raise requests.TooManyRedirects(f"Too many redirects for {url}")


def run_on_ui_thread(page: ft.Page | None, callback, *args, **kwargs) -> None:
    """
    Schedule a sync or async callback through Flet's UI loop.

    Flet 0.21 expects Page.run_task handlers to be async; this wrapper keeps
    callers honest while still falling back cleanly in tests or older runtimes.
    """
    if page is None:
        return

    async def runner():
        result = callback(*args, **kwargs)
        if inspect.isawaitable(result):
            await result

    if hasattr(page, "run_task"):
        scheduled = page.run_task(runner)
        if inspect.iscoroutine(scheduled):
            if inspect.getcoroutinestate(scheduled) == inspect.CORO_CLOSED:
                return
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(scheduled)
            else:
                scheduled.close()
    else:
        result = callback(*args, **kwargs)
        if inspect.isawaitable(result):
            logger.debug("Dropped async UI callback because page.run_task is missing")


def validate_proxy(proxy: str) -> bool:
    """
    Validate proxy format.
    Expected: scheme://[user:pass@]host:port
    Restricts localhost and private IPs to prevent SSRF.
    """
    if not proxy or not isinstance(proxy, str):
        # Empty proxy is valid (no proxy)
        return True

    proxy = proxy.strip()
    if not proxy:
        return True

    # Check length
    if len(proxy) > 2048:
        return False

    try:
        parsed = urlparse(proxy)
        if not parsed.scheme or not parsed.scheme.startswith(
            ("http", "https", "socks4", "socks5")
        ):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Block loopback and private/reserved IPs to prevent SSRF
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
            ):
                return False
        except ValueError:
            # Reject invalid numeric IPs like 999.999.999.999
            if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", hostname):
                return False

        # Port validation
        if parsed.port is not None:
            if not 1 <= parsed.port <= 65535:
                return False

        return True

    except Exception:  # pylint: disable=broad-exception-caught
        return False


def validate_rate_limit(rate_limit: str) -> bool:
    """Validate rate limit (e.g. 50K, 1.5M)."""
    if rate_limit is None:
        # None is valid (no limit)
        return True

    if not isinstance(rate_limit, str):
        # Non-string false unless it's explicitly None handled above
        return False

    s = rate_limit.strip()
    if not s:
        return True

    if s == "0":
        return False

    # Prevent extremely long strings
    if len(s) > 20:
        return False

    # Require a unit when using a decimal; allow integer without unit
    # e.g., 500K, 1.5M, 1000
    int_only = re.compile(r"^[1-9]\d*(?:/s)?$", re.IGNORECASE)
    with_unit = re.compile(r"^[1-9]\d*(\.\d+)?[KMGT](?:/s)?$", re.IGNORECASE)

    return bool(int_only.match(s) or with_unit.match(s))


def validate_output_template(template: str) -> bool:
    """
    Validate output template.
    Must not be absolute and must not contain parent directory references.
    """
    if not template or not isinstance(template, str):
        return False

    if ".." in template:
        return False

    try:
        path = Path(template)
        if path.is_absolute():
            return False
    except Exception:  # pylint: disable=broad-exception-caught
        return False

    return True


def validate_download_path(path_str: str | None) -> bool:
    """
    Validate download path. Empty/None is allowed (defaults apply).
    Attempts to create the directory if it doesn't exist.
    """
    if not path_str:
        return True

    if not isinstance(path_str, str):
        return False

    try:
        raw_path = Path(path_str).expanduser()
        if not raw_path.is_absolute():
            raw_path = (Path.cwd() / raw_path).resolve()

        raw_path.mkdir(parents=True, exist_ok=True)
        return raw_path.exists() and raw_path.is_dir() and os.access(raw_path, os.W_OK)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Invalid download path '%s': %s", path_str, e)
        return False


# Directories that must never be used as the source of a user-initiated
# import. This is a denylist rather than a home-only allowlist because users
# legitimately keep link lists on removable media, in /tmp, or on secondary
# drives; blocking those was a usability defect with no security benefit
# (the path always comes from a native file picker).
_DENIED_SYSTEM_DIRS: tuple[str, ...] = (
    "/etc",
    "/bin",
    "/sbin",
    "/usr",
    "/var",
    "/proc",
    "/sys",
    "/dev",
    "/boot",
    "/lib",
    "/lib64",
    "/root",
    # macOS exposes the same locations under /private (/etc is a symlink to
    # private/etc), so a resolved path never matches the plain entries above.
    "/private/etc",
    "/private/var/audit",
    "/private/var/db",
    "/private/var/log",
    "/private/var/root",
    "/private/var/spool",
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
)

#: Temporary locations that stay importable even though some sit under a denied
#: prefix (``/var/tmp``) or are reached through a symlinked parent
#: (``/private/var/folders`` on macOS). Matched against the *resolved* path, so a
#: symlink pointing out of a temp directory is still denied.
_ALLOWED_TEMP_DIRS: tuple[str, ...] = (
    "/tmp",
    "/var/tmp",
    "/var/folders",
    "/private/tmp",
    "/private/var/tmp",
    "/private/var/folders",
)


def _path_matches_prefix(normalized: str, prefixes: tuple[str, ...]) -> bool:
    """True when ``normalized`` is one of ``prefixes`` or lives inside it."""
    return any(
        normalized == prefix.lower().replace("\\", "/")
        or normalized.startswith(prefix.lower().replace("\\", "/") + "/")
        for prefix in prefixes
    )


def is_safe_path(filepath: str) -> bool:
    """
    Check whether a user-chosen file path is safe to read.

    Rejects well-known system locations (``/etc``, ``/proc``, ``C:\\Windows``,
    …) while allowing user-chosen locations such as the home directory,
    temporary directories, removable media, and secondary drives.

    Both the resolved path and the logical path the user typed are checked.
    Resolution alone is not enough on macOS, where ``/etc/passwd`` resolves to
    ``/private/etc/passwd``; the logical form keeps such paths denied, while the
    resolved form keeps a symlink that escapes a temporary directory out.
    """
    try:
        if not isinstance(filepath, str) or not filepath.strip():
            return False
        if "\x00" in filepath:
            return False

        logical = (
            os.path.normpath(os.path.expanduser(filepath)).lower().replace("\\", "/")
        )
        resolved = str(Path(filepath).resolve()).lower().replace("\\", "/")

        # Temp directories are legitimate import sources even when they live
        # under a denied prefix, but only when the file really is in temp.
        if _path_matches_prefix(resolved, _ALLOWED_TEMP_DIRS):
            return True

        if _path_matches_prefix(resolved, _DENIED_SYSTEM_DIRS):
            return False
        if _path_matches_prefix(logical, _DENIED_SYSTEM_DIRS):
            return False

        # Existence/permission checks belong to the caller; this is a policy
        # check on the path itself.
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        return False


# pylint: disable=invalid-name
_ffmpeg_available_cache: bool | None = None


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system path with timeout and caching."""
    global _ffmpeg_available_cache
    if _ffmpeg_available_cache is not None:
        return _ffmpeg_available_cache

    result = [False]

    def check():
        try:
            # check_output is better than which for some path envs
            # but shutil.which is safer/faster
            result[0] = shutil.which("ffmpeg") is not None
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("FFmpeg check error: %s", str(e))

    thread = threading.Thread(target=check, daemon=True)
    thread.start()
    thread.join(timeout=1.0)

    _ffmpeg_available_cache = result[0]
    return result[0]


def _resolve_preferred_download_path(preferred_path: str | None) -> str | None:
    """Resolve a preferred download path if provided and writable."""
    if not preferred_path or not isinstance(preferred_path, str):
        return None

    try:
        raw_path = Path(preferred_path).expanduser()
        if not raw_path.is_absolute():
            raw_path = (Path.cwd() / raw_path).resolve()

        # Create if missing
        raw_path.mkdir(parents=True, exist_ok=True)

        if raw_path.exists() and raw_path.is_dir() and os.access(raw_path, os.W_OK):
            return str(raw_path)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Preferred download path invalid: %s", e)
    return None


def get_default_download_path(preferred_path: str | None = None) -> str:
    """Get a safe default download path for the current platform."""
    resolved = _resolve_preferred_download_path(preferred_path)
    if resolved:
        return resolved

    try:
        # Check for Android/iOS specific
        home = Path.home()
        downloads = home / "Downloads"
        if downloads.exists() and os.access(downloads, os.W_OK):
            return str(downloads)
        if os.access(home, os.W_OK):
            return str(home)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug("Failed to resolve default download path: %s", exc)
    return "."


# pylint: disable=too-many-return-statements


def open_folder(path: str, page: ft.Page | None = None) -> bool:
    """
    Opens a folder in the system file manager.

    Args:
        path: The path to open.
        page: Optional Flet page (required for mobile/web fallback).
    """
    if not path or not isinstance(path, str):
        return False

    try:
        # Resolve path with security checks
        abs_path = os.path.abspath(os.path.expanduser(path))

        # Canonicalize path to prevent symlink attacks
        try:
            abs_path = os.path.realpath(abs_path)
        except (OSError, ValueError) as e:
            logger.warning("Failed to canonicalize path %s: %s", path, e)
            return False

        # Security check: Ensure it's a directory
        if not os.path.exists(abs_path):
            logger.warning("Path not found: %s", abs_path)
            return False

        if not os.path.isdir(abs_path):
            # If it's a file, get parent
            abs_path = os.path.dirname(abs_path)

        # Mobile / Web Logic
        if page and page.platform in [  # type: ignore
            ft.PagePlatform.ANDROID,
            ft.PagePlatform.IOS,
        ]:
            # Try launch_url with file scheme
            # Note: Mobile sandboxing often prevents this without specific permissions/plugins
            # but this is the best Flet effort.
            page.launch_url(f"file://{abs_path}")  # type: ignore
            return True

        if page and page.platform == ft.PagePlatform.MACOS:  # type: ignore
            # If running as macOS app bundle (not in browser)
            if sys.platform != "darwin":  # Remote browser?
                return False

        sys_plat = platform.system()

        if sys_plat == "Windows":
            # pylint: disable=no-member
            os.startfile(abs_path)  # type: ignore
            return True

        cmd = ["open", abs_path] if sys_plat == "Darwin" else ["xdg-open", abs_path]

        # pylint: disable=consider-using-with
        # Use Popen to avoid blocking
        # Redirect stdout/stderr to avoid leaking descriptors or output
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Failed to open folder: %s", str(e))
        return False


# pylint: disable=too-many-return-statements


def play_file(path: str, page: ft.Page | None = None) -> bool:
    """
    Opens/Plays a file in the default system application.

    Args:
        path: The path of the file to play.
        page: Optional Flet page (required for mobile/web fallback).
    """
    if not path or not isinstance(path, str):
        return False

    try:
        abs_path = os.path.abspath(os.path.expanduser(path))

        # Canonicalize path to prevent symlink attacks
        try:
            abs_path = os.path.realpath(abs_path)
        except (OSError, ValueError) as e:
            logger.warning("Failed to canonicalize path %s: %s", path, e)
            return False

        if not os.path.exists(abs_path):
            return False

        # Ensure it's a file, not a directory
        if not os.path.isfile(abs_path):
            logger.warning("Path is not a file: %s", abs_path)
            return False

        # Mobile / Web Logic
        if page and page.platform in [  # type: ignore
            ft.PagePlatform.ANDROID,
            ft.PagePlatform.IOS,
        ]:
            page.launch_url(f"file://{abs_path}")  # type: ignore
            return True

        if page and page.platform == ft.PagePlatform.MACOS:  # type: ignore
            if sys.platform != "darwin":
                return False

        sys_plat = platform.system()

        if sys_plat == "Windows":
            # pylint: disable=no-member
            os.startfile(abs_path)  # type: ignore
            # pylint: disable=consider-using-with
            return True

        cmd = ["open", abs_path] if sys_plat == "Darwin" else ["xdg-open", abs_path]
        # pylint: disable=consider-using-with
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Failed to play file: %s", str(e))
        return False
