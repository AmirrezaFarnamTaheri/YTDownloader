import unittest
from datetime import datetime, time
from unittest.mock import patch
from download_scheduler import DownloadScheduler


class TestDownloadScheduler(unittest.TestCase):
    def test_prepare_schedule_none(self):
        status, dt = DownloadScheduler.prepare_schedule(None)
        self.assertEqual(status, "Queued")
        self.assertIsNone(dt)

    def test_prepare_schedule_future(self):
        with patch("download_scheduler.datetime") as mock_dt:
            fixed_now = datetime(2023, 1, 1, 10, 0, 0)
            mock_dt.now.return_value = fixed_now
            mock_dt.combine = datetime.combine

            target_time = time(11, 0)
            status, dt_res = DownloadScheduler.prepare_schedule(target_time)

            self.assertEqual(dt_res, datetime(2023, 1, 1, 11, 0))
            self.assertIn("Scheduled", status)

    def test_prepare_schedule_past(self):
        with patch("download_scheduler.datetime") as mock_dt:
            fixed_now = datetime(2023, 1, 1, 10, 0, 0)
            mock_dt.now.return_value = fixed_now
            mock_dt.combine = datetime.combine

            target_time = time(9, 0)
            status, dt_res = DownloadScheduler.prepare_schedule(target_time)

            self.assertEqual(dt_res, datetime(2023, 1, 2, 9, 0))

    def test_prepare_schedule_invalid_type(self):
        with self.assertRaises(TypeError):
            DownloadScheduler.prepare_schedule("10:00")
