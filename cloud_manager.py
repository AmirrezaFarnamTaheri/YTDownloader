import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class CloudManager:
    """
    Manages cloud uploads.
    Currently supports: Google Drive (via PyDrive2).
    """

    def __init__(self):
        self.enabled = False
        self.credentials_path = "client_secrets.json"  # Standard PyDrive2 file
        self.settings_path = "settings.yaml"  # PyDrive2 settings

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
            raise FileNotFoundError(f"File not found: {file_path}")

        if provider == "google_drive":
            self._upload_to_google_drive(file_path)
        else:
            raise NotImplementedError(f"Provider {provider} not supported yet.")

    def _upload_to_google_drive(self, file_path: str):
        """
        Upload logic for Google Drive using PyDrive2.
        Requires client_secrets.json in the working directory.
        """
        if not os.path.exists(self.credentials_path):
            logger.warning(
                f"Google Drive {self.credentials_path} not found. Skipping upload."
            )
            raise Exception(
                "Google Drive not configured (missing client_secrets.json)."
            )

        try:
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive

            # Automatic authentication (requires user interaction on first run or saved creds)
            gauth = GoogleAuth()

            # Try to load saved credentials
            if os.path.exists("mycreds.txt"):
                gauth.LoadCredentialsFile("mycreds.txt")

            if gauth.credentials is None:
                # This might open a browser window which is not ideal for headless,
                # but for desktop app it is expected.
                # In robust backend, we handle this carefully.
                # For now, we assume it works or fails if no interaction possible.
                # To avoid blocking indefinitely in headless:
                if os.environ.get("HEADLESS_MODE"):
                    raise Exception(
                        "Cannot authenticate in headless mode without saved creds."
                    )
                gauth.LocalWebserverAuth()
            elif gauth.access_token_expired:
                gauth.Refresh()
            else:
                gauth.Authorize()

            gauth.SaveCredentialsFile("mycreds.txt")

            drive = GoogleDrive(gauth)

            file_name = os.path.basename(file_path)
            file_drive = drive.CreateFile({"title": file_name})
            file_drive.SetContentFile(file_path)
            file_drive.Upload()
            logger.info(f"Successfully uploaded {file_name} to Google Drive.")

        except ImportError:
            logger.error("PyDrive2 not installed.")
            raise Exception("PyDrive2 dependency missing.")
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
            raise
