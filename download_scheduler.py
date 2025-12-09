"""
Download scheduler logic.
"""

from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from typing import Optional, Tuple, Union


class DownloadScheduler:
    """Helper for scheduling downloads."""

    # pylint: disable=too-few-public-methods

    @staticmethod
    def prepare_schedule(
        scheduled_time: Optional[Union[dt_time, datetime]],
    ) -> Tuple[str, Optional[datetime]]:
        """
        Calculate status and scheduled datetime based on desired time.

        Args:
            scheduled_time: Time object (datetime.time) or datetime for scheduling, or None

        Returns:
            Tuple of (status_string, scheduled_datetime)

        Raises:
            TypeError: If scheduled_time is not None, datetime.time, or datetime instance
        """
        status = "Queued"
        sched_dt = None

        if scheduled_time is not None:
            # Validate input type
            if isinstance(scheduled_time, datetime):
                sched_dt = scheduled_time
                status = f"Scheduled ({sched_dt.strftime('%Y-%m-%d %H:%M')})"
            elif isinstance(scheduled_time, dt_time):
                now = datetime.now()
                sched_dt = datetime.combine(now.date(), scheduled_time)
                if sched_dt < now:
                    sched_dt += timedelta(days=1)
                status = f"Scheduled ({sched_dt.strftime('%H:%M')})"
            else:
                raise TypeError(
                    f"scheduled_time must be datetime.time or datetime instance, got {type(scheduled_time)}"
                )

        return status, sched_dt
