import yt_dlp

def download_video(url, playlist=False, video_format='best'):
    """
    Downloads a video or playlist from the given URL using yt-dlp.
    """
    try:
        ydl_opts = {
            'format': video_format,
            'playlist': playlist,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("Download complete.")
    except Exception as e:
        print(f"An error occurred: {e}")
