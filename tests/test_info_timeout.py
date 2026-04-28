from concurrent.futures import TimeoutError as FuturesTimeoutError

from downloader.info import get_video_info


class FakeFuture:
    def __init__(self):
        self.cancelled = False

    def result(self, timeout=None):
        raise FuturesTimeoutError()

    def cancel(self):
        self.cancelled = True


class FakeExecutor:
    def __init__(self, max_workers=1):
        self.max_workers = max_workers
        self.future = FakeFuture()
        self.shutdown_calls = []

    def submit(self, callback):
        self.callback = callback
        return self.future

    def shutdown(self, wait=True, cancel_futures=False):
        self.shutdown_calls.append(
            {"wait": wait, "cancel_futures": cancel_futures}
        )


def test_get_video_info_timeout_cancels_without_waiting(monkeypatch):
    fake_executor = FakeExecutor()

    monkeypatch.setattr(
        "downloader.info.ThreadPoolExecutor", lambda max_workers=1: fake_executor
    )
    monkeypatch.setattr("downloader.info.INFO_EXTRACTION_TIMEOUT", 0.01)
    monkeypatch.setattr(
        "downloader.info.TelegramExtractor.is_telegram_url", lambda url: False
    )

    result = get_video_info("https://example.com/watch")

    assert result is None
    assert fake_executor.future.cancelled is True
    assert fake_executor.shutdown_calls == [
        {"wait": False, "cancel_futures": True}
    ]
