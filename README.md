# YLF Downloader

[![Release](https://img.shields.io/github/v/release/younglonelyfeel/YLF_Download?style=flat-square)](https://github.com/younglonelyfeel/YLF_Download/releases)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

A modern, lightweight GUI wrapper for **yt-dlp** built with **CustomTkinter**. Designed for efficiency with a "Mini Flash Mode" overlay, smart clipboard automation, and drag-and-drop support.

## Features

* **Mini Flash Mode:** Compact 280x140 floating window (Always-on-top) with visual status feedback (Green/Red flash).
* **Smart Automation:** Auto-detects URLs, extracts metadata, and copies captions to the clipboard instantly.
* **Multi-Platform Support:** Seamlessly downloads from YouTube, TikTok, Facebook, Pinterest, and more.
* **Drag & Drop:** Native support for dragging links directly into the application window.
* **Safe & Stable:** Integrated rate limiting and anti-spam protection to prevent IP blocking (429 Errors).

## Installation & Usage

### For End Users (Windows)

1.  Go to the **[Releases Page](https://github.com/younglonelyfeel/YLF_Download/releases)**.
2.  Download the latest `YLF_Downloader.zip`.
3.  Extract the archive.
4.  Ensure `ffmpeg.exe` is placed in the root folder.
5.  Run `YLF Downloader.exe`.

### For Developers (Build from Source)

**Prerequisites:**
* Python 3.10+
* FFmpeg installed and added to PATH.

**Setup:**

```bash
# Clone the repository
git clone [https://github.com/younglonelyfeel/YLF_Download.git](https://github.com/younglonelyfeel/YLF_Download.git)
cd YLF_Download

# Install dependencies
pip install customtkinter yt-dlp tkinterdnd2

# Run the application
python main.py
```

## Configuration

* **Download Path:** Default is `Downloads/YLF-Downloads`.
* **Cookies:** Place your `cookies.txt` in the root directory for authentication support.

---
*Developed by @younglonelyfeel*
