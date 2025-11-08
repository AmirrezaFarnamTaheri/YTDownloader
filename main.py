import argparse
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download videos from YouTube.")
    parser.add_argument("url", help="The URL of the video or playlist to download.")
    parser.add_argument("-p", "--playlist", action="store_true", help="Download a playlist.")
    parser.add_argument("-f", "--format", default="best", help="The video format to download (e.g., 'best', 'mp4', 'webm').")

    args = parser.parse_args()

    download_video(args.url, args.playlist, args.format)
