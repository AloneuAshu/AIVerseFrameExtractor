# Storyboard Extractor & Generator

A modern toolkit for filmmakers to convert scripts into structured visual storyboards with dynamic vector (SVG) generation.

## Features
- **Multi-line Script Input**: Paste your entire script for processing.
- **Auto Scene Detection**: Automatically detects `INT./EXT.` markers, locations, and time of day.
- **Smart Enrichment**: Infers shot types (Wide, Close-up) and camera movements (Pan, Track) from text.
- **Dynamic Vector Rendering**: Generates stylized SVG panels based on scene metadata.
- **Artistic Styles**: Choose from Cinematic, Pencil Sketch, Comic, Film Noir, or Anime.
- **Export Options**: Export your storyboard as a professional PDF, PowerPoint presentation, or raw SVG folder.
- **Modern Dark UI**: Premium visual experience using CustomTkinter.

## Setup Instructions

1. **Install Dependencies**:
   Ensure you have Python 3.10+ installed. Then run:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```

## Modular Architecture
- `main.py`: The entry point and UI logic.
- `scene_parser.py`: Regex-based script analyzer.
- `storyboard_generator.py`: High-level manager connecting parser and renderer.
- `vector_renderer.py`: Logic for drawing SVG panels using `svgwrite`.
- `export_manager.py`: PDF (`reportlab`) and PPT (`python-pptx`) generation logic.

## Usage
1. Type or paste your script in the left panel.
2. Ensure scene headers follow the standard format: `INT. LOCATION - TIME` or `EXT. LOCATION - TIME`.
3. Select an artistic style from the dropdown.
4. Click **GENERATE STORYBOARD**.
5. Use the navigation buttons to preview scenes.
6. Use the export buttons at the bottom right to save your work.
