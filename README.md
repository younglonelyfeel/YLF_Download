# YLF Downloader

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

A modern, lightweight GUI wrapper for `yt-dlp` built with **CustomTkinter**.
Designed for efficiency with a "Mini Flash Mode" overlay and clipboard automation.

## Features

- **Multi-Platform Support**: Downloads from YouTube, TikTok, Facebook, Pinterest, etc.
- **Smart Clipboard**: Auto-detects URLs and fetches metadata instantly.
- **Mini Mode**: Compact 280x140 floating window for multitasking.
- **High Performance**: Optimized `onedir` build for instant startup.
- **Auto-Processing**: Automatic video extraction and caption copying.

## Installation & Usage

### For End Users (Windows)
1. Go to the [Releases Page](../../releases).
2. Download the latest `YLF_Tool.zip`.
3. Extract the archive.
4. Ensure `ffmpeg.exe` is placed in the root folder.
5. Run `YLF_Tool.exe`.

### For Developers (Build from Source)

**Prerequisites:**
- Python 3.10+
- FFmpeg installed and added to PATH.

**Setup:**
```bash
# Clone the repository
git clone [https://github.com/younglonelyfeel/YLF-Update.git](https://github.com/younglonelyfeel/YLF-Update.git)
cd YLF-Update

# Install dependencies
pip install -r requirements.txt

# Run the application
python YLF_Downloader.py
