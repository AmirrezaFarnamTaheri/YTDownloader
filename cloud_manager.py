import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Compatibility shim: ensure pydrive2 exposes auth/drive as attributes on its
# top-level package if available. Some tests patch "pydrive2.auth" directly,
# which expects this attribute-style access to work.
try:  # pragma: no cover - environment dependent
    import pydrive2 as _pyd2  # type: ignore

    try:
        from pydrive2 import auth as _pyd2_auth  # type: ignore

        if not hasattr(_pyd2, "auth"):
            _pyd2.auth = _pyd2_auth  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        from pydrive2 import drive as _pyd2_drive  # type: ignore

        if not hasattr(_pyd2, "drive"):
            _pyd2.drive = _pyd2_drive  # type: ignore[attr-defined]
    except Exception:
        pass
except Exception:
    # If pydrive2 isn't installed, normal import paths and error handling apply.
    pass


class CloudManager:
    """
    Manages cloud uploads.
    Currently supports: Google Drive (via PyDrive2).
    """

    def __init__(self):
        logger.debug("Initializing CloudManager...")
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
            error_msg = f"File not found for upload: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"Initiating upload for {file_path} to {provider}")

        if provider == "google_drive":
            self._upload_to_google_drive(file_path)
        else:
            logger.error(f"Provider {provider} not supported.")
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
            from pydrive2.auth import GoogleAuth  # type: ignore
            from pydrive2.drive import GoogleDrive  # type: ignore

            # Automatic authentication (requires user interaction on first run or saved creds)
            logger.debug("Authenticating with Google Drive...")
            gauth = GoogleAuth()

            # Try to load saved credentials
            if os.path.exists("mycreds.txt"):
                gauth.LoadCredentialsFile("mycreds.txt") # type: ignore

            if gauth.credentials is None: # type: ignore
                # This might open a browser window which is not ideal for headless,
                # but for desktop app it is expected.
                # In robust backend, we handle this carefully.
                # For now, we assume it works or fails if no interaction possible.
                # To avoid blocking indefinitely in headless:
                if os.environ.get("HEADLESS_MODE"):
                    raise Exception(
                        "Cannot authenticate in headless mode without saved creds."
                    )
                logger.info("Opening local webserver for Google authentication...")
                gauth.LocalWebserverAuth() # type: ignore
            elif gauth.access_token_expired: # type: ignore
                logger.info("Refreshing Google Drive access token...")
                gauth.Refresh() # type: ignore
            else:
                gauth.Authorize() # type: ignore

            gauth.SaveCredentialsFile("mycreds.txt") # type: ignore

            drive = GoogleDrive(gauth) # type: ignore

            file_name = os.path.basename(file_path)
            logger.debug(f"Uploading file content: {file_name}")
            file_drive = drive.CreateFile({"title": file_name}) # type: ignore
            file_drive.SetContentFile(file_path) # type: ignore
            file_drive.Upload() # type: ignore
            logger.info(f"Successfully uploaded {file_name} to Google Drive.")

        except ImportError:
            logger.error("PyDrive2 not installed.")
            raise Exception("PyDrive2 dependency missing.")
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}", exc_info=True)
            raise

    # Missing methods expected by sync_manager
    def is_authenticated(self) -> bool:
         """Check if we have valid credentials."""
         try:
            from pydrive2.auth import GoogleAuth # type: ignore
            if os.path.exists("mycreds.txt"):
                 gauth = GoogleAuth()
                 gauth.LoadCredentialsFile("mycreds.txt") # type: ignore
                 return gauth.credentials is not None # type: ignore
         except Exception:
              pass
         return False

    def get_file_id(self, filename: str) -> Optional[str]:
         """Find file ID by name."""
         try:
             from pydrive2.auth import GoogleAuth # type: ignore
             from pydrive2.drive import GoogleDrive # type: ignore

             if not self.is_authenticated():
                  return None

             gauth = GoogleAuth()
             gauth.LoadCredentialsFile("mycreds.txt") # type: ignore
             drive = GoogleDrive(gauth) # type: ignore

             # Search
             query = f"title = '{filename}' and trashed = false"
             file_list = drive.ListFile({'q': query}).GetList() # type: ignore

             if file_list:
                  return file_list[0]['id'] # type: ignore
         except Exception as e:
              logger.error(f"Failed to get file ID: {e}")
         return None

    def read_file_content(self, file_id: str) -> Optional[str]:
        """Read content of a file given its ID."""
        try:
             from pydrive2.auth import GoogleAuth # type: ignore
             from pydrive2.drive import GoogleDrive # type: ignore

             if not self.is_authenticated():
                  return None

             gauth = GoogleAuth()
             gauth.LoadCredentialsFile("mycreds.txt") # type: ignore
             drive = GoogleDrive(gauth) # type: ignore

             f = drive.CreateFile({'id': file_id}) # type: ignore
             return f.GetContentString() # type: ignore
        except Exception as e:
             logger.error(f"Failed to read file content: {e}")
        return None
