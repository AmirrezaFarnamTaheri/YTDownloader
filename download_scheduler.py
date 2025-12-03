"""
Download scheduler logic.
"""

from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from typing import Optional, Tuple


class DownloadScheduler:
    """Helper for scheduling downloads."""

    # pylint: disable=too-few-public-methods

    @staticmethod
    def prepare_schedule(
        scheduled_time: Optional[dt_time],
    ) -> Tuple[str, Optional[datetime]]:
        """
        Calculate status and scheduled datetime based on desired time.
        """
        status = "Queued"
        sched_dt = None

        if scheduled_time:
            now = datetime.now()
            sched_dt = datetime.combine(now.date(), scheduled_time)
            if sched_dt < now:
                sched_dt += timedelta(days=1)
            status = f"Scheduled ({sched_dt.strftime('%H:%M')})"

        return status, sched_dt
