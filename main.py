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

# ─── Configuration & Persistence ──────────────────────────────────────────
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SettingsManager:
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
                    return {**cls.DEFAULTS, **json.load(f)}
            except: return cls.DEFAULTS
        return cls.DEFAULTS

    @classmethod
    def save(cls, settings):
        with open(cls.FILE_PATH, "w") as f:
            json.dump(settings, f, indent=4)

# ─── Theme ──────────────────────────────────────────────────────────────────
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

# ─── FFmpeg Support ────────────────────────────────────────────────────────
class FFmpegManager:
    @classmethod
    def get_ffmpeg(cls):
        path = SettingsManager.load().get("ffmpeg_path")
        if path and os.path.exists(path): return path
        return "ffmpeg" if shutil.which("ffmpeg") else None

    @classmethod
    def get_ffprobe(cls):
        path = SettingsManager.load().get("ffprobe_path")
        if path and os.path.exists(path): return path
        return "ffprobe" if shutil.which("ffprobe") else None

# ─── View: Single Frame Extractor ──────────────────────────────────────────
class SingleFrameView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.video_path = None
        self.video_info = {}
        self.output_path = None
        self._init_ui()

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Layout: Two columns (Controls vs Preview)
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Left Column: controls
        ctrl = ctk.CTkFrame(content, width=320, fg_color=Theme.PANEL_BG, corner_radius=15)
        ctrl.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        ctrl.grid_propagate(False)

        ctk.CTkLabel(ctrl, text="SINGLE EXTRACTION", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.ACCENT).pack(pady=(20, 10))
        
        self.select_btn = ctk.CTkButton(ctrl, text="📂 Select Video", height=45, fg_color=Theme.ACCENT, command=self.select_video)
        self.select_btn.pack(fill="x", padx=20, pady=10)

        # Info Card
        self.info_card = ctk.CTkFrame(ctrl, fg_color=Theme.CARD_BG, corner_radius=10)
        self.info_card.pack(fill="x", padx=20, pady=10)
        self.lbl_file = self._label(self.info_card, "📄 No video selected")
        self.lbl_res  = self._label(self.info_card, "📐 Res: --")
        self.lbl_fps  = self._label(self.info_card, "🔢 FPS: --")

        # Format
        ctk.CTkLabel(ctrl, text="Quality Format", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack(anchor="w", padx=25)
        self.fmt_var = ctk.StringVar(value="PNG (Lossless)")
        ctk.CTkOptionMenu(ctrl, variable=self.fmt_var, values=["PNG (Lossless)", "JPEG (High)", "BMP"], fg_color=Theme.CARD_BG).pack(fill="x", padx=20, pady=(2, 20))

        # Extract
        self.extract_btn = ctk.CTkButton(ctrl, text="⚡ Extract Last Frame", height=50, fg_color=Theme.SUCCESS, state="disabled", command=self.extract)
        self.extract_btn.pack(fill="x", padx=20, pady=(20, 5))
        
        self.prog = ctk.CTkProgressBar(ctrl, height=8, fg_color=Theme.BG_DARK)
        self.prog.pack(fill="x", padx=20, pady=5)
        self.prog.set(0)

        # Right Column: Preview
        self.preview_box = ctk.CTkFrame(content, fg_color=Theme.PANEL_BG, corner_radius=15)
        self.preview_box.grid(row=0, column=1, sticky="nsew")
        self.preview_box.grid_rowconfigure(0, weight=1)
        self.preview_box.grid_columnconfigure(0, weight=1)
        
        self.pre_lbl = ctk.CTkLabel(self.preview_box, text="Preview Area", font=ctk.CTkFont(size=14), text_color=Theme.CARD_BG)
        self.pre_lbl.grid(row=0, column=0)

        # Bottom Bar
        bot = ctk.CTkFrame(self, height=60, fg_color="transparent")
        bot.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.status = ctk.CTkLabel(bot, text="Ready", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_DIM)
        self.status.pack(side="left")

    def _label(self, parent, txt):
        l = ctk.CTkLabel(parent, text=txt, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM, anchor="w")
        l.pack(fill="x", padx=15, pady=2)
        return l

    def select_video(self):
        p = filedialog.askopenfilename()
        if p:
            self.video_path = p
            self.lbl_file.configure(text=f"📄 {os.path.basename(p)}", text_color=Theme.TEXT_MAIN)
            self.status.configure(text="Analyzing...", text_color=Theme.ACCENT)
            threading.Thread(target=self._probe, daemon=True).start()

    def _probe(self):
        ff = FFmpegManager.get_ffprobe()
        if not ff: return
        try:
            cmd = [ff, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", self.video_path]
            data = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
            v = next(s for s in data["streams"] if s["codec_type"] == "video")
            dur = float(data["format"]["duration"])
            self.video_info = {"w": v["width"], "h": v["height"], "fps": v["r_frame_rate"], "dur": dur}
            self.after(0, self._apply_probe)
        except: pass

    def _apply_probe(self):
        self.lbl_res.configure(text=f"📐 {self.video_info['w']}x{self.video_info['h']}", text_color=Theme.TEXT_MAIN)
        self.lbl_fps.configure(text=f"🔢 {self.video_info['fps']} FPS", text_color=Theme.TEXT_MAIN)
        self.extract_btn.configure(state="normal")
        self.status.configure(text="✅ Video Loaded", text_color=Theme.SUCCESS)

    def extract(self):
        self.extract_btn.configure(state="disabled", text="⏳ ...")
        self.prog.set(0.4)
        threading.Thread(target=self._run_ffmpeg, daemon=True).start()

    def _run_ffmpeg(self):
        ff = FFmpegManager.get_ffmpeg()
        ext = ".png" if "PNG" in self.fmt_var.get() else ".jpg"
        folder = os.path.join(os.path.dirname(self.video_path), f"{os.path.splitext(os.path.basename(self.video_path))[0]}_Frames")
        os.makedirs(folder, exist_ok=True)
        out = os.path.join(folder, f"LastFrame_{int(time.time())}{ext}")
        
        cmd = [ff, "-y", "-ss", str(max(0, self.video_info['dur']-1)), "-i", self.video_path, "-update", "1", "-vframes", "1", out]
        subprocess.run(cmd, capture_output=True)
        
        if os.path.exists(out):
            self.output_path = out
            self.after(0, lambda: self._on_done(out))

    def _on_done(self, out):
        self.extract_btn.configure(state="normal", text="⚡ Extract Last Frame")
        self.prog.set(1.0)
        self.status.configure(text=f"✅ Saved to folder", text_color=Theme.SUCCESS)
        img = Image.open(out)
        img.thumbnail((600, 400))
        ctk_img = ctk.CTkImage(img, size=(img.width, img.height))
        self.pre_lbl.configure(image=ctk_img, text="")
        self.pre_lbl.image = ctk_img

# ─── View: Batch Extractor ────────────────────────────────────────────────
class BatchView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self._init_ui()

    def _init_ui(self):
        ctk.CTkLabel(self, text="📦 Batch Suite", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=40)
        ctk.CTkLabel(self, text="This feature is coming in the next AIVerse update!", text_color=Theme.TEXT_DIM).pack()
        ctk.CTkButton(self, text="Upgrade to Pro (Coming Soon)", state="disabled", fg_color=Theme.CARD_BG).pack(pady=20)

# ─── View: Storyboard ─────────────────────────────────────────────────────
class StoryboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self._init_ui()

    def _init_ui(self):
        ctk.CTkLabel(self, text="🎞️ Storyboard Generator", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=40)
        ctk.CTkLabel(self, text="Generate cinematic contact sheets automatically.", text_color=Theme.TEXT_DIM).pack()
        ctk.CTkButton(self, text="Waitlist Active", state="disabled", fg_color=Theme.CARD_BG).pack(pady=20)

# ─── Main Application ──────────────────────────────────────────────────────
class AIVerseStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AIVerseStudio - Suite")
        self.geometry("1300x850")
        self.configure(fg_color=Theme.BG_DARK)

        self.current_view = None
        self._init_ui()
        self.switch_tab("extract")

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar Navigation
        self.nav = ctk.CTkFrame(self, width=280, fg_color=Theme.PANEL_BG, corner_radius=0)
        self.nav.grid(row=0, column=0, sticky="nsew")
        self.nav.grid_propagate(False)

        # Header
        header = ctk.CTkFrame(self.nav, fg_color="transparent")
        header.pack(fill="x", pady=30, padx=20)
        ctk.CTkLabel(header, text="🌌", font=ctk.CTkFont(size=40)).pack()
        ctk.CTkLabel(header, text="AIVerseStudio", font=ctk.CTkFont(size=20, weight="bold")).pack()
        ctk.CTkLabel(header, text="Creative Suite v2.0", font=ctk.CTkFont(size=10), text_color=Theme.TEXT_DIM).pack()

        # Nav Buttons
        self.btns = {}
        self._nav_btn("extract", "⚡  Single Extract", "extract")
        self._nav_btn("batch", "📦  Batch Suite", "batch")
        self._nav_btn("story", "🎞️  Storyboard", "story")
        
        # Spacer
        ctk.CTkFrame(self.nav, fg_color="transparent", height=100).pack(fill="y", expand=True)

        # Settings
        self._nav_btn("settings", "⚙️  Global Settings", "settings")

        # Main Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

    def _nav_btn(self, id, text, tab_name):
        btn = ctk.CTkButton(self.nav, text=text, height=50, corner_radius=10,
                            anchor="w", fg_color="transparent", hover_color=Theme.CARD_BG,
                            text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=13),
                            command=lambda: self.switch_tab(tab_name))
        btn.pack(fill="x", padx=15, pady=5)
        self.btns[id] = btn

    def switch_tab(self, tab):
        if self.current_view: self.current_view.destroy()
        
        # UI Selection State
        for k, v in self.btns.items():
            v.configure(fg_color="transparent", text_color=Theme.TEXT_DIM)
        
        if tab == "extract":
            self.current_view = SingleFrameView(self.container, self)
            self.btns["extract"].configure(fg_color=Theme.ACCENT, text_color="white")
        elif tab == "batch":
            self.current_view = BatchView(self.container, self)
            self.btns["batch"].configure(fg_color=Theme.ACCENT, text_color="white")
        elif tab == "story":
            self.current_view = StoryboardView(self.container, self)
            self.btns["story"].configure(fg_color=Theme.ACCENT, text_color="white")
        elif tab == "settings":
            self.show_settings()
            return
            
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Global Settings")
        win.geometry("500x450")
        win.configure(fg_color=Theme.BG_DARK)
        win.transient(self); win.grab_set()

        ctk.CTkLabel(win, text="⚙️ Preferences", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        s = SettingsManager.load()
        
        f_ent = self._st_row(win, "FFmpeg Path", s["ffmpeg_path"])
        p_ent = self._st_row(win, "FFprobe Path", s["ffprobe_path"])

        def save():
            SettingsManager.save({"ffmpeg_path": f_ent.get(), "ffprobe_path": p_ent.get()})
            win.destroy()
        ctk.CTkButton(win, text="Save Changes", fg_color=Theme.ACCENT, command=save).pack(pady=20)

    def _st_row(self, win, lbl, val):
        f = ctk.CTkFrame(win, fg_color="transparent")
        f.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(f, text=lbl, text_color=Theme.TEXT_DIM).pack(anchor="w")
        e = ctk.CTkEntry(f, width=400, fg_color=Theme.PANEL_BG)
        e.insert(0, val); e.pack(pady=5)
        return e

if __name__ == "__main__":
    app = AIVerseStudio()
    app.mainloop()
