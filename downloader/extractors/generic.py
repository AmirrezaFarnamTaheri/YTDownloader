"""
Generic extractor module.
Fallback for unsupported URLs or direct file links if structure demands an extractor interface.
Actually aliases GenericDownloader in current architecture, but good for completeness.
"""

from downloader.engines.generic import GenericDownloader

class GenericExtractor:
    """
    Generic extractor.
    """
    @staticmethod
    def extract(url: str, output_path: str, progress_hook=None, cancel_token=None) -> dict:
        return GenericDownloader.download(url, output_path, progress_hook, cancel_token)
