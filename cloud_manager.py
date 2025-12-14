"""
Cloud Manager module.
"""

import logging
import os

logger = logging.getLogger(__name__)


# Compatibility shim for pydrive2 attributes if needed
try:  # pragma: no cover - environment dependent
    import pydrive2 as _pyd2  # type: ignore

    try:
        from pydrive2 import auth as _pyd2_auth  # type: ignore

        if not hasattr(_pyd2, "auth"):
            _pyd2.auth = _pyd2_auth  # type: ignore[attr-defined]
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    try:
        from pydrive2 import drive as _pyd2_drive  # type: ignore

        if not hasattr(_pyd2, "drive"):
            _pyd2.drive = _pyd2_drive  # type: ignore[attr-defined]
    except Exception:  # pylint: disable=broad-exception-caught
        pass
except Exception:  # pylint: disable=broad-exception-caught
    pass

# Import PyDrive2 classes at module level
try:
    from pydrive2.auth import GoogleAuth  # type: ignore
    from pydrive2.drive import GoogleDrive  # type: ignore
except (ImportError, Exception):  # pylint: disable=broad-exception-caught
    GoogleAuth = None
    GoogleDrive = None


class CloudManager:
    """
    Manages cloud uploads and downloads.
    Currently supports: Google Drive (via PyDrive2).
    """

    def __init__(self):
        logger.debug("Initializing CloudManager...")
        self.enabled = False
        # Use environment variable or secure path in user directory
        self.credentials_path = os.environ.get(
            "GOOGLE_DRIVE_CREDENTIALS_PATH",
            os.path.expanduser("~/.streamcatch/client_secrets.json"),
        )
        self.settings_path = os.environ.get(
            "GOOGLE_DRIVE_SETTINGS_PATH",
            os.path.expanduser("~/.streamcatch/settings.yaml"),
        )

    def upload_file(self, file_path: str, provider: str = "google_drive"):
        """
        Uploads a file to the specified cloud provider.

        Args:
            file_path: Path to the file to upload.
            provider: Cloud provider ('google_drive').

        Raises:
            FileNotFoundError: If file does not exist.
            Exception: If upload fails or credentials missing.
        """
        if not os.path.exists(file_path):
            error_msg = f"File not found for upload: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info("Initiating upload for %s to %s", file_path, provider)

        if provider == "google_drive":
            self._upload_to_google_drive(file_path)
        else:
            logger.error("Provider %s not supported.", provider)
            raise NotImplementedError(f"Provider {provider} not supported yet.")

    def download_file(
        self, filename: str, destination_path: str, provider: str = "google_drive"
    ) -> bool:
        """
        Downloads a file from the cloud provider by filename (exact match).

        Args:
            filename: Name of the file in cloud storage.
            destination_path: Local path to save the file.
            provider: Cloud provider ('google_drive').

        Returns:
            True if successful, False otherwise.
        """
        logger.info("Initiating download for %s from %s", filename, provider)

        if provider == "google_drive":
            return self._download_from_google_drive(filename, destination_path)
        logger.error("Provider %s not supported.", provider)
        return False

    def _get_google_drive_client(self):
        """Helper to authenticate and return a GoogleDrive client."""
        # Check if PyDrive2 is installed
        if GoogleAuth is None or GoogleDrive is None:
            logger.error("PyDrive2 not installed.")
            # pylint: disable=broad-exception-raised
            raise Exception("PyDrive2 dependency missing.")

        # 1. Check for client_secrets.json
        if not os.path.exists(self.credentials_path):
            logger.warning(
                "Google Drive %s not found. Skipping auth.", self.credentials_path
            )
            # pylint: disable=broad-exception-raised
            raise Exception(
                "Google Drive not configured (missing client_secrets.json)."
            )

        # 2. Check for pre-authenticated creds in env var if file missing
        mycreds_path = os.path.expanduser("~/.streamcatch/mycreds.txt")
        if not os.path.exists(mycreds_path):
            creds_content = os.environ.get("GOOGLE_CREDS_CONTENT")
            if creds_content:
                logger.info("Restoring mycreds.txt from environment variable.")
                # Ensure directory exists
                os.makedirs(os.path.dirname(mycreds_path), exist_ok=True)
                # Write with secure permissions (owner read/write only)
                with open(
                    mycreds_path,
                    "w",
                    encoding="utf-8",
                    opener=lambda p, f: os.open(p, f, 0o600),
                ) as f:
                    f.write(creds_content)
                # Ensure permissions are set (in case opener didn't work on all platforms)
                try:
                    os.chmod(mycreds_path, 0o600)
                except OSError:
                    logger.warning(
                        "Could not set secure permissions on credentials file"
                    )

        try:
            # Automatic authentication
            logger.debug("Authenticating with Google Drive...")
            gauth = GoogleAuth()

            # Try to load saved credentials
            mycreds_path = os.path.expanduser("~/.streamcatch/mycreds.txt")
            if os.path.exists(mycreds_path):
                gauth.LoadCredentialsFile(mycreds_path)  # type: ignore

            if gauth.credentials is None:  # type: ignore
                # In headless environments without pre-auth, this fails.
                if os.environ.get("HEADLESS_MODE") or os.environ.get("CI"):
                    # pylint: disable=broad-exception-raised
                    raise Exception(
                        "Cannot authenticate in headless mode without saved creds."
                    )
                logger.info("Opening local webserver for Google authentication...")
                gauth.LocalWebserverAuth()  # type: ignore
            elif gauth.access_token_expired:  # type: ignore
                logger.info("Refreshing Google Drive access token...")
                gauth.Refresh()  # type: ignore
            else:
                gauth.Authorize()  # type: ignore

            # Save credentials with secure permissions
            mycreds_path = os.path.expanduser("~/.streamcatch/mycreds.txt")
            os.makedirs(os.path.dirname(mycreds_path), exist_ok=True)
            gauth.SaveCredentialsFile(mycreds_path)  # type: ignore
            # Set secure permissions after save
            try:
                os.chmod(mycreds_path, 0o600)
            except OSError:
                logger.warning("Could not set secure permissions on credentials file")
            return GoogleDrive(gauth)  # type: ignore

        except ImportError as exc:
            # Should be caught by top check, but safe guard
            logger.error("PyDrive2 not installed.")
            # pylint: disable=broad-exception-raised
            raise Exception("PyDrive2 dependency missing.") from exc
        except Exception as e:
            logger.error("Google Drive auth failed: %s", e, exc_info=True)
            raise

    def _upload_to_google_drive(self, file_path: str):
        """Upload logic for Google Drive."""
        try:
            drive = self._get_google_drive_client()

            file_name = os.path.basename(file_path)

            # Escape single quotes in filename to prevent query injection
            # Google Drive API uses single quotes for string literals
            escaped_name = file_name.replace("'", "\\'")
            query = f"title = '{escaped_name}' and trashed = false"
            file_list = drive.ListFile({"q": query}).GetList()  # type: ignore

            if file_list:
                file_drive = file_list[0]
                logger.info("Updating existing file: %s", file_name)
            else:
                file_drive = drive.CreateFile({"title": file_name})  # type: ignore
                logger.info("Creating new file: %s", file_name)

            file_drive.SetContentFile(file_path)  # type: ignore
            file_drive.Upload()  # type: ignore
            logger.info("Successfully uploaded %s to Google Drive.", file_name)

        except Exception as e:
            logger.error("Google Drive upload failed: %s", e)
            raise

    def _download_from_google_drive(self, filename: str, destination_path: str) -> bool:
        """Download logic for Google Drive."""
        try:
            drive = self._get_google_drive_client()

            # Search for file - escape single quotes to prevent query injection
            escaped_filename = filename.replace("'", "\\'")
            query = f"title = '{escaped_filename}' and trashed = false"
            file_list = drive.ListFile({"q": query}).GetList()  # type: ignore

            if not file_list:
                logger.warning("File '%s' not found in Google Drive.", filename)
                return False

            # Take the first match
            file_drive = file_list[0]
            logger.info("Downloading %s (ID: %s)", filename, file_drive["id"])

            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination_path)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)

            file_drive.GetContentFile(destination_path)  # type: ignore
            return True

        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error("Google Drive download failed: %s", e)
            return False
