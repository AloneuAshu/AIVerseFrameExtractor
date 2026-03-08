from scene_parser import ScriptParser
from vector_renderer import VectorRenderer
import os
import json

SETTINGS_FILE = "settings.json"

class StoryboardGenerator:
    def __init__(self, output_dir="storyboard_export"):
        self.output_dir = output_dir
        self.svg_dir = os.path.join(output_dir, "svg")
        os.makedirs(self.svg_dir, exist_ok=True)
        self.renderer = VectorRenderer(self.svg_dir)
        self.scenes = []

    def _get_api_key(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f).get("gemini_api_key", "")
            except: pass
        return ""

    def process_script(self, text, style, progress_callback=None):
        """Parse script and generate storyboard panels using local high-fidelity renderer."""
        self.scenes = ScriptParser.parse_text(text)
        svg_paths, png_paths = [], []

        for i, scene in enumerate(self.scenes):
            if progress_callback:
                progress_callback(i, len(self.scenes))

            print(f"[Renderer] Generating Local Sketch for Scene {i+1}...")
            svg_path, png_path = self.renderer.render_scene(scene, style, i)

            svg_paths.append(svg_path)
            png_paths.append(png_path)

        if progress_callback:
            progress_callback(len(self.scenes), len(self.scenes))

        # Build the combined strip sheet
        try:
            self.renderer.build_strip_sheet("AIVerseStudio — The Flash")
        except Exception as e:
            print(f"[Strip] Sheet build skipped: {e}")

        return self.scenes, svg_paths, png_paths

    def get_scene_data(self, index):
        if 0 <= index < len(self.scenes):
            return self.scenes[index]
        return None
