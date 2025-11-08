# YTDownloader

YTDownloader is a modern, user-friendly desktop application for downloading videos and subtitles from YouTube. Built with Python, Tkinter, and the powerful `yt-dlp` library, it offers a seamless and feature-rich experience for all your video downloading needs.

## Features

- **Modern & Intuitive UI**: A clean and stylish interface built with `ttkthemes` that is easy to navigate.
- **Tabbed Layout**: A well-organized, tabbed interface that separates video, audio, subtitle, and playlist options for a streamlined user experience.
- **Fetch Video Information**: Instantly fetch and display video details, including the title, thumbnail, and duration, before you download.
- **High-Quality Downloads**: Download videos in the highest available quality, or choose from a variety of video and audio formats.
- **Playlist Support**: Download entire playlists with a single click.
- **Subtitle & Transcript Downloads**: Download subtitles and transcripts in various formats (SRT, VTT, etc.) and languages (when available).
- **Custom Output Path**: Choose exactly where you want to save your downloaded files.
- **Real-Time Progress**: A visual progress bar keeps you informed of your download's status in real-time.
- **Clear UI**: A "Clear" button that resets the UI to its initial state, allowing you to easily start a new download.
- **Standalone Executable**: The application is packaged as a single executable file, so you don't need to install Python or any dependencies to use it.

## User Walkthrough

Here’s a step-by-step guide to using YTDownloader:

1.  **Enter a Video URL**: Paste the URL of the YouTube video or playlist you want to download into the "Video URL" field.

2.  **Fetch Video Info**: Click the "Fetch Info" button to see the video's title, thumbnail, and duration, as well as a list of available video, audio, and subtitle options.

3.  **Select Your Options**:
    *   **Video Tab**: Choose your desired video format from the dropdown menu.
    *   **Audio Tab**: Choose your desired audio format from the dropdown menu.
    *   **Subtitles Tab**: If subtitles are available, select your preferred language and format.
    *   **Playlist Tab**: If you entered a playlist URL, check the "Download Playlist" box to download the entire playlist.

4.  **Choose an Output Path**: Click the "Browse..." button to select the folder where you want to save your download. If you don't choose a path, the file will be saved in the same directory as the application.

5.  **Start the Download**: Click the "Download" button to begin. The progress bar will show the download's progress, and a status message will keep you updated.

6.  **Clear the UI**: When you're finished, click the "Clear" button to reset the UI and prepare for a new download.

## Installation

You can download the latest version of YTDownloader as a standalone executable from the project's releases page. No installation is required—just download the file and run it.

## Building from Source

If you prefer to build the application from the source code, follow these steps:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/ytdownloader.git
    cd ytdownloader
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application**:
    ```bash
    python main.py
    ```

5.  **Build the Executable**:
    To create a standalone executable, run the following command:
    ```bash
    pyinstaller --onefile --windowed --noconsole main.py
    ```
    The executable will be located in the `dist` directory.

## Contributing

Contributions are welcome! If you have any ideas for new features or improvements, feel free to open an issue or submit a pull request.
