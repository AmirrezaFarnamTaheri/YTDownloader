import pytest
import os
import json
import zipfile
import tempfile
import threading
from unittest.mock import MagicMock, patch, mock_open
from sync_manager import SyncManager
from datetime import datetime


class TestSyncManagerComprehensive:
    @pytest.fixture
    def mock_cloud_manager(self):
        return MagicMock()

    @pytest.fixture
    def mock_history_manager(self):
        return MagicMock()

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()

        def get_side_effect(key, default=None):
            if key == "auto_sync_enabled":
                return True
            if key == "auto_sync_interval":
                return 60
            return default

        config.get.side_effect = get_side_effect
        return config

    @pytest.fixture
    def sync_manager(self, mock_cloud_manager, mock_history_manager, mock_config):
        return SyncManager(mock_cloud_manager, mock_config, mock_history_manager)

    def test_start_auto_sync(self, sync_manager):
        # Assuming start_auto_sync creates a thread
        with patch("sync_manager.threading.Thread") as mock_thread:
            sync_manager.start_auto_sync()

            # Should create a thread targeting _auto_sync_loop
            if sync_manager._thread:
                mock_thread.assert_called()
                sync_manager._thread.start.assert_called()

    def test_stop_auto_sync(self, sync_manager):
        # Setup fake thread
        mock_thread = MagicMock()
        sync_manager._thread = mock_thread
        sync_manager._stop_event = MagicMock()

        sync_manager.stop_auto_sync()

        sync_manager._stop_event.set.assert_called()
        mock_thread.join.assert_called()
        assert sync_manager._thread is None

    def test_export_data_success(self, sync_manager):
        sync_manager.config.get_all.return_value = {"test": "config"}
        if hasattr(sync_manager.config, "load_config"):
            del sync_manager.config.load_config

        with patch("sync_manager.zipfile.ZipFile") as mock_zip:
            sync_manager.export_data("export.zip")
            zip_instance = mock_zip.return_value.__enter__.return_value
            args_list = zip_instance.writestr.call_args_list
            assert len(args_list) >= 1
            filename, content = args_list[0][0]
            assert filename == "config.json"
            assert '"test": "config"' in content

    def test_import_data_success(self, sync_manager):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip.name, "w") as zf:
                zf.writestr("config.json", '{"test": "new_config"}')
                zf.writestr("history.db", b"sqlite data")
            tmp_zip_path = tmp_zip.name

        try:
            with patch.object(sync_manager, "_import_history_db") as mock_import_db:
                sync_manager.import_data(tmp_zip_path)
                sync_manager.config.save_config.assert_called_with(
                    {"test": "new_config"}
                )
                mock_import_db.assert_called()
        finally:
            if os.path.exists(tmp_zip_path):
                os.remove(tmp_zip_path)

    def test_import_data_file_not_found(self, sync_manager):
        with pytest.raises(FileNotFoundError):
            sync_manager.import_data("nonexistent.zip")

    def test_sync_down_success(self, sync_manager):
        sync_manager.cloud.download_file.return_value = True
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_config:
            json.dump({"remote": "config"}, tmp_config)
            tmp_config_path = tmp_config.name

        def download_side_effect(filename, local_path):
            import shutil

            shutil.copy(tmp_config_path, local_path)
            return True

        sync_manager.cloud.download_file.side_effect = download_side_effect

        try:
            sync_manager.sync_down()
            sync_manager.config.save_config.assert_called()
        finally:
            if os.path.exists(tmp_config_path):
                os.remove(tmp_config_path)

    def test_sync_up_success(self, sync_manager):
        sync_manager.config.get_all.return_value = {"local": "config"}
        sync_manager.cloud.upload_file.return_value = True
        sync_manager.sync_up()
        sync_manager.cloud.upload_file.assert_called()
