import yt_dlp
import os

def get_video_info(url):
    """
    Fetches video metadata without downloading the video.
    """
    ydl_opts = {'quiet': True, 'listsubtitles': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        subtitles = {}
        if 'subtitles' in info_dict and info_dict['subtitles']:
            for lang, subs in info_dict['subtitles'].items():
                formats = [sub['ext'] for sub in subs]
                subtitles[lang] = formats

        formats = info_dict.get('formats', [])
        video_streams = []
        audio_streams = []
        for f in formats:
            if f.get('vcodec') != 'none':
                video_streams.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f.get('resolution'),
                    'fps': f.get('fps'),
                    'acodec': f.get('acodec'),
                })
            elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                audio_streams.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'abr': f.get('abr'),
                })

        return {
            'title': info_dict.get('title', 'N/A'),
            'thumbnail': info_dict.get('thumbnail', None),
            'duration': info_dict.get('duration_string', 'N/A'),
            'subtitles': subtitles,
            'video_streams': video_streams,
            'audio_streams': audio_streams,
        }

def download_video(url, progress_hook, playlist=False, video_format='best', output_path='.', subtitle_lang=None, subtitle_format='srt'):
    """
    Downloads a video or playlist from the given URL using yt-dlp.
    """
    ydl_opts = {
        'format': video_format,
        'playlist': playlist,
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
    }

    if subtitle_lang:
        ydl_opts.update({
            'writesubtitles': True,
            'subtitleslangs': [subtitle_lang],
            'subtitlesformat': subtitle_format,
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
