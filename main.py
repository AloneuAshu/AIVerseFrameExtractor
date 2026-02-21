import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import json
import os
import threading
from PIL import Image, ImageTk
import time
import shutil
import pyperclip
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ─── Configuration & Persistence ──────────────────────────────────────────
class SettingsManager:
    """Manages application settings persisted in a JSON file."""
    FILE_PATH = "settings.json"
    DEFAULTS = {
        "ffmpeg_path": r"C:\Users\srika\FFMeg\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
        "ffprobe_path": r"C:\Users\srika\FFMeg\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffprobe.exe"
    }

    @classmethod
    def load(cls):
        if os.path.exists(cls.FILE_PATH):
            try:
                with open(cls.FILE_PATH, "r") as f:
                    data = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**cls.DEFAULTS, **data}
            except:
                return cls.DEFAULTS
        return cls.DEFAULTS

    @classmethod
    def save(cls, settings):
        try:
            with open(cls.FILE_PATH, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

# ─── Theme ──────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class Theme:
    ACCENT      = "#6366F1"  # Indigo 500
    ACCENT_HOVER = "#4F46E5" # Indigo 600
    SUCCESS     = "#10B981"  # Emerald 500
    ERROR       = "#EF4444"  # Red 500
    BG_DARK     = "#0F172A"  # Slate 900
    PANEL_BG    = "#1E293B"  # Slate 800
    CARD_BG     = "#334155"  # Slate 700
    TEXT_MAIN   = "#F8FAFC"  # Slate 50
    TEXT_DIM    = "#94A3B8"  # Slate 400

# ─── FFmpeg Management ──────────────────────────────────────────────────────
class FFmpegManager:
    """Handles discovery and execution of FFmpeg/FFprobe."""
    
    @classmethod
    def get_ffmpeg(cls):
        """Returns the best available ffmpeg path."""
        settings = SettingsManager.load()
        path = settings.get("ffmpeg_path")
        if path and os.path.exists(path):
            return path
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        return None

    @classmethod
    def get_ffprobe(cls):
        """Returns the best available ffprobe path."""
        settings = SettingsManager.load()
        path = settings.get("ffprobe_path")
        if path and os.path.exists(path):
            return path
        if shutil.which("ffprobe"):
            return "ffprobe"
        return None

# ─── Main Application ───────────────────────────────────────────────────────
class LastFrameExtractor(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AIVerseStudio - LastFrame Extractor")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(fg_color=Theme.BG_DARK)

        # State Variables
        self.video_path  = None
        self.output_path = None
        self.video_info  = {}
        self.extraction_history = []

        self._init_ui()

    def _init_ui(self):
        # Configure Grid
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Area
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=320, fg_color=Theme.PANEL_BG, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Brand / Logo
        brand_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # Settings Cog at top right of brand frame
        settings_btn = ctk.CTkButton(brand_frame, text="⚙️", width=30, height=30,
                                    fg_color="transparent", hover_color=Theme.CARD_BG,
                                    text_color=Theme.TEXT_DIM, command=self.show_settings)
        settings_btn.place(relx=1.0, rely=0, anchor="ne")

        logo_lbl = ctk.CTkLabel(brand_frame, text="🌌", font=ctk.CTkFont(size=44))
        logo_lbl.pack(pady=(10, 5))
        
        title_lbl = ctk.CTkLabel(brand_frame, text="AIVerseStudio", 
                                 font=ctk.CTkFont(size=22, weight="bold"),
                                 text_color=Theme.TEXT_MAIN)
        title_lbl.pack(pady=(0, 0))
        
        sub_lbl = ctk.CTkLabel(brand_frame, text="Next-Gen Video Intelligence", 
                               font=ctk.CTkFont(size=12),
                               text_color=Theme.TEXT_DIM)
        sub_lbl.pack(pady=(5, 10))

        # Action Buttons
        self.select_btn = ctk.CTkButton(sidebar, text="📂  Select Video File",
                                       height=50, font=ctk.CTkFont(size=14, weight="bold"),
                                       fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER,
                                       command=self.handle_select_video)
        self.select_btn.pack(fill="x", padx=30, pady=(10, 20))

        # Metadata Card
        self.info_card = ctk.CTkFrame(sidebar, fg_color=Theme.CARD_BG, corner_radius=12)
        self.info_card.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.info_card, text="VIDEO PROPERTIES", 
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=Theme.ACCENT).pack(anchor="w", padx=15, pady=(12, 5))
        
        self.lbl_file = self._create_info_label(self.info_card, "📄 No file selected")
        self.lbl_res  = self._create_info_label(self.info_card, "📐 Resolution: --")
        self.lbl_dur  = self._create_info_label(self.info_card, "⏱ Duration: --")
        self.lbl_fps  = self._create_info_label(self.info_card, "🔢 FPS: --")
        self.lbl_codec = self._create_info_label(self.info_card, "🎞 Codec: --", bottom=15)

        # Settings Card
        settings_card = ctk.CTkFrame(sidebar, fg_color=Theme.CARD_BG, corner_radius=12)
        settings_card.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(settings_card, text="EXPORT SETTINGS", 
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=Theme.ACCENT).pack(anchor="w", padx=15, pady=(12, 5))
        
        ctk.CTkLabel(settings_card, text="Format", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack(anchor="w", padx=15)
        self.format_var = ctk.StringVar(value="PNG (Lossless)")
        self.format_menu = ctk.CTkOptionMenu(settings_card, variable=self.format_var,
                                            values=["PNG (Lossless)", "JPEG (High Quality)", "BMP (Raw)"],
                                            fg_color=Theme.PANEL_BG, button_color=Theme.ACCENT)
        self.format_menu.pack(fill="x", padx=15, pady=(2, 12))

        # Progress Section
        self.extract_btn = ctk.CTkButton(sidebar, text="⚡  Extract Last Frame",
                                        height=54, font=ctk.CTkFont(size=15, weight="bold"),
                                        fg_color=Theme.SUCCESS, hover_color="#059669",
                                        state="disabled",
                                        command=self.handle_extract)
        self.extract_btn.pack(fill="x", padx=30, pady=(20, 5))
        
        self.progress_bar = ctk.CTkProgressBar(sidebar, height=8, fg_color=Theme.CARD_BG, progress_color=Theme.ACCENT)
        self.progress_bar.pack(fill="x", padx=30, pady=5)
        self.progress_bar.set(0)
        
        self.status_lbl = ctk.CTkLabel(sidebar, text="Awaiting input...", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM)
        self.status_lbl.pack(pady=(2, 20))

    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Preview Container
        self.preview_container = ctk.CTkFrame(main, fg_color=Theme.PANEL_BG, corner_radius=20, border_width=1, border_color=Theme.CARD_BG)
        self.preview_container.grid(row=0, column=0, sticky="nsew")
        self.preview_container.grid_rowconfigure(0, weight=1)
        self.preview_container.grid_columnconfigure(0, weight=1)

        self.preview_placeholder = ctk.CTkLabel(self.preview_container, 
                                                text="PREVIEW AREA\n\nDrop a video or click select\nto see the extracted frame here",
                                                font=ctk.CTkFont(size=16), text_color=Theme.CARD_BG)
        self.preview_placeholder.grid(row=0, column=0)
        
        self.preview_img_label = None

        # Bottom Controls
        controls = ctk.CTkFrame(main, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        
        self.result_path_lbl = ctk.CTkLabel(controls, text="", font=ctk.CTkFont(size=12), text_color=Theme.SUCCESS)
        self.result_path_lbl.pack(side="left")

        self.copy_btn = ctk.CTkButton(controls, text="📋 Copy Path", width=120, height=36,
                                     fg_color=Theme.CARD_BG, hover_color=Theme.PANEL_BG,
                                     state="disabled", command=self.copy_path)
        self.copy_btn.pack(side="right", padx=(10, 0))

        self.open_folder_btn = ctk.CTkButton(controls, text="📂 Open Folder", width=120, height=36,
                                           fg_color=Theme.CARD_BG, hover_color=Theme.PANEL_BG,
                                           state="disabled", command=self.open_folder)
        self.open_folder_btn.pack(side="right")

    def _create_info_label(self, parent, text, bottom=5):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM, anchor="w")
        lbl.pack(fill="x", padx=15, pady=(2, bottom))
        return lbl

    # ─── Logic ──────────────────────────────────────────────────────────────────
    
    def handle_select_video(self):
        path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv *.m4v *.ts"), ("All Files", "*.*")]
        )
        if path:
            self.video_path = path
            self._on_video_selected()

    def _on_video_selected(self):
        filename = os.path.basename(self.video_path)
        self.lbl_file.configure(text=f"📄 {filename}", text_color=Theme.TEXT_MAIN)
        self.status_lbl.configure(text="Probing video stream...", text_color=Theme.ACCENT)
        self.progress_bar.set(0.1)
        
        threading.Thread(target=self._probe_video, daemon=True).start()

    def _probe_video(self):
        ffprobe = FFmpegManager.get_ffprobe()
        if not ffprobe:
            self._update_status("❌ FFprobe not found", Theme.ERROR)
            return

        try:
            cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", self.video_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            data = json.loads(result.stdout)
            
            video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
            if not video_stream:
                raise ValueError("No video stream found")

            # Extract info
            w = video_stream.get("width", 0)
            h = video_stream.get("height", 0)
            codec = video_stream.get("codec_name", "unknown").upper()
            
            r_fps = video_stream.get("r_frame_rate", "0/0")
            try:
                n, d = map(int, r_fps.split("/"))
                fps = round(n/d, 2) if d != 0 else 0
            except: fps = "--"
            
            dur = float(data.get("format", {}).get("duration", 0))
            dur_str = time.strftime('%H:%M:%S', time.gmtime(dur)) + f".{int((dur%1)*100):02d}"

            self.video_info = {"width": w, "height": h, "codec": codec, "fps": fps, "duration_sec": dur, "duration_str": dur_str}
            
            self.after(0, self._apply_probe_results)
            
        except Exception as e:
            self._update_status(f"❌ Error: {str(e)}", Theme.ERROR)

    def _apply_probe_results(self):
        vi = self.video_info
        self.lbl_res.configure(text=f"📐 {vi['width']} x {vi['height']}", text_color=Theme.TEXT_MAIN)
        self.lbl_dur.configure(text=f"⏱ {vi['duration_str']}", text_color=Theme.TEXT_MAIN)
        self.lbl_fps.configure(text=f"🔢 {vi['fps']} FPS", text_color=Theme.TEXT_MAIN)
        self.lbl_codec.configure(text=f"🎞 {vi['codec']}", text_color=Theme.TEXT_MAIN)
        
        self.extract_btn.configure(state="normal")
        self.progress_bar.set(0)
        self._update_status("✅ Ready for extraction", Theme.SUCCESS)

    def handle_extract(self):
        if not self.video_path: return
        
        self.extract_btn.configure(state="disabled", text="⏳ Working...")
        self._update_status("Decoding last frame...", Theme.ACCENT)
        self.progress_bar.set(0.4)
        
        threading.Thread(target=self._run_extraction, daemon=True).start()

    def _run_extraction(self):
        ffmpeg = FFmpegManager.get_ffmpeg()
        if not ffmpeg:
            self._update_status("❌ FFmpeg not found", Theme.ERROR)
            return

        fmt_sel = self.format_var.get()
        ext = ".png" if "PNG" in fmt_sel else ".jpg" if "JPEG" in fmt_sel else ".bmp"
        
        # ─── Folder Management ───
        video_dir = os.path.dirname(self.video_path)
        video_stem = os.path.splitext(os.path.basename(self.video_path))[0]
        # Create a dedicated directory for this video's frames
        extraction_dir = os.path.join(video_dir, f"{video_stem}_Frames")
        
        try:
            if not os.path.exists(extraction_dir):
                os.makedirs(extraction_dir)
        except Exception as e:
            self._update_status(f"❌ Folder Error: {str(e)}", Theme.ERROR)
            self.after(0, lambda: self.extract_btn.configure(state="normal", text="⚡  Extract Last Frame"))
            return

        temp_out = os.path.join(extraction_dir, f"tmp_{int(time.time())}{ext}")
        
        # Strategy: Seek to near end and overwrite until EOF
        seek_point = max(0, self.video_info['duration_sec'] - 1.0)
        
        cmd = [
            ffmpeg, "-y",
            "-ss", str(seek_point),
            "-i", self.video_path,
            "-update", "1",
            "-q:v", "1" if ext == ".jpg" else "0",
            temp_out
        ]
        
        try:
            # Run command
            subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if os.path.exists(temp_out) and os.path.getsize(temp_out) > 0:
                # Success - rename to final
                final_path = os.path.join(extraction_dir, f"{video_stem}_LastFrame{ext}")
                
                # Check for collisions within the dedicated folder
                counter = 1
                while os.path.exists(final_path):
                    final_path = os.path.join(extraction_dir, f"{video_stem}_LastFrame_{counter}{ext}")
                    counter += 1
                
                os.rename(temp_out, final_path)
                self.output_path = final_path
                self.after(0, lambda: self._on_extraction_complete(final_path))
            else:
                self._update_status("❌ Extraction failed", Theme.ERROR)
                self.after(0, lambda: self.extract_btn.configure(state="normal", text="⚡  Extract Last Frame"))
                
        except Exception as e:
            self._update_status(f"❌ Error: {str(e)}", Theme.ERROR)
            self.after(0, lambda: self.extract_btn.configure(state="normal", text="⚡  Extract Last Frame"))

    def _on_extraction_complete(self, path):
        self._update_status("✅ Extraction successful!", Theme.SUCCESS)
        self.progress_bar.set(1.0)
        self.extract_btn.configure(state="normal", text="⚡  Extract Last Frame")
        
        name = os.path.basename(path)
        self.result_path_lbl.configure(text=f"Saved: {name}")
        self.copy_btn.configure(state="normal")
        self.open_folder_btn.configure(state="normal")
        
        self._show_preview(path)

    def _show_preview(self, path):
        try:
            img = Image.open(path)
            
            # Container dimensions
            cw = self.preview_container.winfo_width() - 60
            ch = self.preview_container.winfo_height() - 60
            if cw < 400: cw = 600
            if ch < 300: ch = 400
            
            img.thumbnail((cw, ch), Image.Resampling.LANCZOS)
            
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            
            if self.preview_img_label:
                self.preview_img_label.destroy()
            
            self.preview_placeholder.grid_forget()
            self.preview_img_label = ctk.CTkLabel(self.preview_container, image=ctk_img, text="")
            self.preview_img_label.grid(row=0, column=0)
            self.preview_img_label.image = ctk_img # Keep reference
            
        except Exception as e:
            print(f"Preview error: {e}")

    # ─── Helpers ────────────────────────────────────────────────────────────────

    def _update_status(self, text, color=Theme.TEXT_DIM):
        self.after(0, lambda: self.status_lbl.configure(text=text, text_color=color))

    def copy_path(self):
        if self.output_path:
            pyperclip.copy(self.output_path)
            self._update_status("📋 Path copied to clipboard", Theme.SUCCESS)

    def open_folder(self):
        if self.output_path:
            os.startfile(os.path.dirname(self.output_path))

    def show_settings(self):
        """Opens the Settings Modal."""
        settings_win = ctk.CTkToplevel(self)
        settings_win.title("Global App Settings")
        settings_win.geometry("500x400")
        settings_win.configure(fg_color=Theme.BG_DARK)
        settings_win.transient(self) # Keep on top of main window
        settings_win.grab_set()      # Modal
        
        ctk.CTkLabel(settings_win, text="Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        container = ctk.CTkFrame(settings_win, fg_color=Theme.PANEL_BG, corner_radius=12)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        settings = SettingsManager.load()
        
        # FFmpeg Path
        ctk.CTkLabel(container, text="FFmpeg Executable Path", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack(anchor="w", padx=20, pady=(20, 5))
        ffmpeg_entry = ctk.CTkEntry(container, width=400, fg_color=Theme.CARD_BG)
        ffmpeg_entry.insert(0, settings.get("ffmpeg_path", ""))
        ffmpeg_entry.pack(padx=20, pady=(0, 10))
        
        def browse_ffmpeg():
            p = filedialog.askopenfilename(title="Select ffmpeg.exe", filetypes=[("Executable", "*.exe"), ("All Files", "*.*")])
            if p:
                ffmpeg_entry.delete(0, "end")
                ffmpeg_entry.insert(0, p)
        
        ctk.CTkButton(container, text="📁 Browse FFmpeg", height=32, fg_color=Theme.CARD_BG, command=browse_ffmpeg).pack(padx=20, pady=(0, 10))

        # FFprobe Path
        ctk.CTkLabel(container, text="FFprobe Executable Path", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack(anchor="w", padx=20, pady=(10, 5))
        ffprobe_entry = ctk.CTkEntry(container, width=400, fg_color=Theme.CARD_BG)
        ffprobe_entry.insert(0, settings.get("ffprobe_path", ""))
        ffprobe_entry.pack(padx=20, pady=(0, 10))
        
        def browse_ffprobe():
            p = filedialog.askopenfilename(title="Select ffprobe.exe", filetypes=[("Executable", "*.exe"), ("All Files", "*.*")])
            if p:
                ffprobe_entry.delete(0, "end")
                ffprobe_entry.insert(0, p)

        ctk.CTkButton(container, text="📁 Browse FFprobe", height=32, fg_color=Theme.CARD_BG, command=browse_ffprobe).pack(padx=20, pady=(0, 10))

        def save_all():
            new_settings = {
                "ffmpeg_path": ffmpeg_entry.get().strip(),
                "ffprobe_path": ffprobe_entry.get().strip()
            }
            SettingsManager.save(new_settings)
            self._update_status("✅ Settings saved", Theme.SUCCESS)
            settings_win.destroy()

        ctk.CTkButton(settings_win, text="💾 Save Changes", height=45, fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, command=save_all).pack(pady=(0, 20))

if __name__ == "__main__":
    app = LastFrameExtractor()
    app.mainloop()
