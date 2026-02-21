# 🌌 AIVerseStudio - LastFrame Extractor

A professional, AI-powered desktop utility designed for frame-accurate video extraction with 4K quality preservation.

## ✨ Features
- **AIVerse Precision**: Uses advanced FFmpeg seeking to capture the absolute terminal frame of any video.
- **Next-Gen UI**: Sleek, modern Slate/Indigo design optimized for high-performance workflows.
- **Global App Settings**: Easily configure external tool paths (FFmpeg/FFprobe) via the built-in settings interface.
- **Auto-Organization**: Automatically creates dedicated subfolders for each video project to keep your workspace clean.
- **Lossless Export**: Support for 1:1 pixel-perfect PNG extractions.

## 🚀 Quick Start
Run the Python script directly:
```bash
python main.py
```

## 🛠 Building the Portable App
To create a standalone EXE with the new branding:
```bash
python -m PyInstaller --noconsole --onefile --name "AIVerseStudio_Extractor" main.py
```

## 📝 Technologies
- **CustomTkinter**: Premium UI components.
- **FFmpeg**: The core extraction engine.
- **Pillow**: Image processing and rendering.
- **Pyperclip**: Integrated clipboard management.
