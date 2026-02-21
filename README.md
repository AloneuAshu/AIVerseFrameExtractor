# 🌌 AIVerseStudio - Creative Suite

A professional, high-performance desktop utility designed for cinematic video frame extraction and storyboard generation.

![AIVerseStudio](https://raw.githubusercontent.com/AloneuAshu/AIVerseFrameExtractor/main/AIVerseLogo.jpeg)

## ✨ Pro Features
- **🏠 Interactive Dashboard**: Instant system health checks (FFmpeg status) and quick-access tool cards.
- **⚡ Precision Extraction**: Absolute terminal frame capture with **True-Shot AI** to skip black frames.
- **🎞️ Timeline Scrubber**: Manually pick the perfect frame from the professional terminal-sequence preview.
- **🎨 Cinematic Storyboard**: Generate high-res strips or download individual shots from the start, middle, and end of any video.
- **📦 Batch Processing**: Process entire directories in seconds with live-log tracking.
- **🍔 UI/UX Pro**: Collapsible sliding sidebar (Hamburger menu) and a **Cinema Viewer** for fullscreen image inspection.
- **🪄 Studio Sharper**: Built-in image enhancement engine for crisp, production-ready outputs.

## 🚀 Download & Installation

### 📥 Auto-Download (Direct)
[**🚀 Click to Download AIVerseStudio.exe**](https://github.com/AloneuAshu/AIVerseFrameExtractor/releases/latest/download/AIVerseStudio.exe)

### Option 1: Standalone Portable EXE (Easiest)
1. Download `AIVerseStudio.exe` from the [latest release](https://github.com/AloneuAshu/AIVerseFrameExtractor/releases).
2. Run it—no installation required!
3. Ensure you have **FFmpeg** installed on your system or configured in the **Preferences** (⚙️) tab within the app.

### Option 2: Developer Setup (Python)
1. **Clone the Repo**:
   ```bash
   git clone https://github.com/AloneuAshu/AIVerseFrameExtractor.git
   cd AIVerseFrameExtractor
   ```
2. **Install Dependencies**:
   ```bash
   pip install customtkinter pillow pyperclip
   ```
3. **Run the App**:
   ```bash
   python main.py
   ```

## ⚙️ Requirements
- **FFmpeg/FFprobe**: Required for video processing.
  - *Note: You can easily point the app to your `ffmpeg.exe` path via the in-app Preferences tab.*

## 🛠️ Building From Source
To bundle the app into a single executable with custom icon:
```bash
python -m PyInstaller --noconsole --onefile --icon "AIVerseLogo.ico" --name "AIVerseStudio" main.py
```

## 📝 Technologies
- **CustomTkinter**: Modern Slate/Indigo UI components.
- **FFmpeg Engine**: Industry-standard video processing.
- **Pillow**: Advanced image enhancement & storyboard merging.
- **Multi-threading**: Keeping the UI responsive during heavy AI tasks.

---
*Created with 🌌 for the AIVerse Community.*
