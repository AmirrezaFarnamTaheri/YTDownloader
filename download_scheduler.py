"""
Download scheduler logic.
"""

import logging
from datetime import datetime, timedelta
from datetime import time as dt_time

logger = logging.getLogger(__name__)


class DownloadScheduler:
    """Helper for scheduling downloads."""

    # pylint: disable=too-few-public-methods

    @staticmethod
    def prepare_schedule(
        scheduled_time: dt_time | datetime | None,
    ) -> tuple[str, datetime | None]:
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
                logger.info("Download scheduled for %s", sched_dt)
            elif isinstance(scheduled_time, dt_time):
                now = datetime.now()
                sched_dt = datetime.combine(now.date(), scheduled_time)
                if sched_dt < now:
                    sched_dt += timedelta(days=1)
                status = f"Scheduled ({sched_dt.strftime('%H:%M')})"
                logger.info("Download scheduled for %s", sched_dt)
            else:
                logger.warning(
                    "Invalid schedule type provided: %s", type(scheduled_time)
                )
                msg = (
                    "scheduled_time must be datetime.time or datetime instance, "
                    f"got {type(scheduled_time)}"
                )
                raise TypeError(msg)
        else:
            logger.debug("No schedule requested; using queued status")

        return status, sched_dt
