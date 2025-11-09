import yt_dlp
import os

def get_video_info(url):
    """
    Fetches video metadata without downloading the video.

    :param url: The URL of the video.
    :return: A dictionary containing video information.
    """
    ydl_opts = {'quiet': True, 'listsubtitles': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)

        # Extract subtitle information
        subtitles = {}
        if 'subtitles' in info_dict and info_dict['subtitles']:
            for lang, subs in info_dict['subtitles'].items():
                formats = [sub['ext'] for sub in subs]
                subtitles[lang] = formats

        # Extract video and audio stream information
        formats = info_dict.get('formats', [])
        video_streams = []
        audio_streams = []
        for f in formats:
            # A video stream has a video codec
            if f.get('vcodec') != 'none':
                video_streams.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f.get('resolution'),
                    'fps': f.get('fps'),
                    'vcodec': f.get('vcodec'),
                    'acodec': f.get('acodec'),
                    'filesize': f.get('filesize'),
                })
            elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                audio_streams.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'abr': f.get('abr'),
                    'acodec': f.get('acodec'),
                    'filesize': f.get('filesize'),
                })

        return {
            'title': info_dict.get('title', 'N/A'),
            'thumbnail': info_dict.get('thumbnail', None),
            'duration': info_dict.get('duration_string', 'N/A'),
            'subtitles': subtitles,
            'video_streams': video_streams,
            'audio_streams': audio_streams,
            'chapters': info_dict.get('chapters', None),
        }

def download_video(url, progress_hook, download_item, playlist=False, video_format='best', output_path='.', subtitle_lang=None, subtitle_format='srt', split_chapters=False, proxy=None, rate_limit=None, cancel_token=None):
    """
    Downloads a video or playlist from the given URL using yt-dlp.

    :param url: The URL of the video or playlist.
    :param progress_hook: A function to be called with progress updates.
    :param download_item: The dictionary representing the download item.
    :param playlist: Whether to download a playlist.
    :param video_format: The format of the video to download.
    :param output_path: The directory to save the downloaded file.
    :param subtitle_lang: The language of the subtitles to download.
    :param subtitle_format: The format of the subtitles.
    :param split_chapters: Whether to split the video into chapters.
    :param proxy: The proxy to use for the download.
    :param rate_limit: The download speed limit.
    :param cancel_token: A token to cancel the download.
    """
    ydl_opts = {
        'format': video_format,
        'playlist': playlist,
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: progress_hook(d, download_item)],
        'continuedl': True,
        'retries': 10,
        'fragment_retries': 10,
    }

    if subtitle_lang:
        ydl_opts.update({
            'writesubtitles': True,
            'subtitleslangs': [subtitle_lang],
            'subtitlesformat': subtitle_format,
        })

    if split_chapters:
        ydl_opts['split_chapters'] = True
        ydl_opts['outtmpl'] = os.path.join(output_path, '%(title)s', '%(section_number)02d - %(section_title)s.%(ext)s')

    if proxy:
        ydl_opts['proxy'] = proxy
    if rate_limit:
        ydl_opts['ratelimit'] = rate_limit
    if cancel_token:
        ydl_opts['progress_hooks'].append(lambda d: cancel_token.check(d))

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except yt_dlp.utils.DownloadError as e:
            if "by user" in str(e):
                return  # Download was cancelled
            raise
