import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import json
import os
import threading
from PIL import Image, ImageTk, ImageEnhance
import time
import shutil
import pyperclip
import sys

# ─── Configuration & Persistence ──────────────────────────────────────────
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SettingsManager:
    FILE_PATH = "settings.json"
    DEFAULTS = {
        "ffmpeg_path": r"C:\Users\srika\FFMeg\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
        "ffprobe_path": r"C:\Users\srika\FFMeg\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffprobe.exe",
        "auto_open": True,
        "studio_sharp": True,
        "skip_black": True
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
    ACCENT      = "#6366F1"
    ACCENT_HOVER = "#4F46E5"
    SUCCESS     = "#10B981"
    ERROR       = "#EF4444"
    BG_DARK     = "#0F172A"
    PANEL_BG    = "#1E293B"
    CARD_BG     = "#334155"
    TEXT_MAIN   = "#F8FAFC"
    TEXT_DIM    = "#94A3B8"

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

    @classmethod
    def probe_video(cls, path):
        ff = cls.get_ffprobe()
        if not ff: return None
        try:
            cmd = [ff, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", path]
            data = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
            v = next(s for s in data["streams"] if s["codec_type"] == "video")
            dur = float(data["format"].get("duration", 0))
            return {"w": v["width"], "h": v["height"], "fps": v["r_frame_rate"], "dur": dur}
        except: return None

# ─── View: Welcome / Home ───────────────────────────────────────────────────
class HomeView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._init_ui()

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        hero = ctk.CTkFrame(self, fg_color=Theme.PANEL_BG, corner_radius=20)
        hero.pack(fill="x", padx=40, pady=(40, 20))
        ctk.CTkLabel(hero, text="Welcome to AIVerseStudio", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(30, 5))
        ctk.CTkLabel(hero, text="Your all-in-one cinematic production toolkit", text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=14)).pack(pady=(0, 30))
        status_f = ctk.CTkFrame(hero, fg_color=Theme.BG_DARK, corner_radius=12)
        status_f.pack(padx=30, pady=(0, 30), fill="x")
        ff_ok = FFmpegManager.get_ffmpeg() is not None
        ff_color = Theme.SUCCESS if ff_ok else Theme.ERROR
        ff_text = "FFmpeg: ONLINE" if ff_ok else "FFmpeg: NOT DETECTED"
        ctk.CTkLabel(status_f, text=ff_text, text_color=ff_color, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=20, pady=10)
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=40, pady=20); actions.grid_columnconfigure((0,1,2), weight=1)
        self._action_card(actions, "⚡", "Single Extract", "Best for precision", lambda: self.app.switch_tab("extract"), 0)
        self._action_card(actions, "📦", "Batch Suite", "Process directories", lambda: self.app.switch_tab("batch"), 1)
        self._action_card(actions, "🎞️", "Storyboard", "Cinema Strips", lambda: self.app.switch_tab("story"), 2)

    def _action_card(self, master, icon, title, sub, cmd, col):
        card = ctk.CTkFrame(master, fg_color=Theme.PANEL_BG, corner_radius=15, height=180)
        card.grid(row=0, column=col, padx=10, sticky="nsew"); card.grid_propagate(False)
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=32)).pack(pady=(25, 5))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=15, weight="bold")).pack()
        ctk.CTkLabel(card, text=sub, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack(pady=(2, 15))
        ctk.CTkButton(card, text="Open Tool", height=32, fg_color=Theme.CARD_BG, hover_color=Theme.ACCENT, command=cmd).pack(pady=(0, 20), padx=20, fill="x")

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
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        content.grid_columnconfigure(1, weight=1); content.grid_rowconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(content, width=320, fg_color=Theme.PANEL_BG, corner_radius=15)
        ctrl.grid(row=0, column=0, sticky="nsew", padx=(0, 20)); ctrl.grid_propagate(False)

        ctk.CTkLabel(ctrl, text="SINGLE EXTRACTION", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.ACCENT).pack(pady=(20, 5))
        self.select_btn = ctk.CTkButton(ctrl, text="📂 Select Video", height=45, fg_color=Theme.ACCENT, command=self.select_video)
        self.select_btn.pack(fill="x", padx=20, pady=10)

        self.info_card = ctk.CTkFrame(ctrl, fg_color=Theme.CARD_BG, corner_radius=10)
        self.info_card.pack(fill="x", padx=20, pady=5)
        self.lbl_file = self._label(self.info_card, "📄 No video selected")
        self.lbl_res  = self._label(self.info_card, "📐 Res: --")
        
        # Format Selection
        ctk.CTkLabel(ctrl, text="Quality Format", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack(anchor="w", padx=25, pady=(10, 0))
        self.fmt_var = ctk.StringVar(value="PNG (Lossless)")
        self.fmt_menu = ctk.CTkOptionMenu(ctrl, variable=self.fmt_var, values=["PNG (Lossless)", "JPEG (High)", "BMP"], fg_color=Theme.CARD_BG)
        self.fmt_menu.pack(fill="x", padx=20, pady=(2, 10))

        # Power Toggles
        self.ai_card = ctk.CTkFrame(ctrl, fg_color="transparent")
        self.ai_card.pack(fill="x", padx=20, pady=5)
        
        s = SettingsManager.load()
        self.skip_black_var = tk.BooleanVar(value=s.get("skip_black", True))
        ctk.CTkCheckBox(self.ai_card, text="True-Shot (Skip Black)", variable=self.skip_black_var, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM, border_color=Theme.ACCENT).pack(anchor="w", pady=2)
        
        self.sharp_var = tk.BooleanVar(value=s.get("studio_sharp", True))
        ctk.CTkCheckBox(self.ai_card, text="Studio Grade Sharper", variable=self.sharp_var, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM, border_color=Theme.ACCENT).pack(anchor="w", pady=2)

        # Actions
        self.scrub_btn = ctk.CTkButton(ctrl, text="🎞️ Open Timeline Scrubber", height=40, fg_color=Theme.CARD_BG, state="disabled", command=self.open_scrubber)
        self.scrub_btn.pack(fill="x", padx=20, pady=(10, 5))

        self.extract_btn = ctk.CTkButton(ctrl, text="⚡ Extract Last Frame", height=50, fg_color=Theme.SUCCESS, font=ctk.CTkFont(weight="bold"), state="disabled", command=self.extract)
        self.extract_btn.pack(fill="x", padx=20, pady=(15, 5))
        
        self.prog = ctk.CTkProgressBar(ctrl, height=8, fg_color=Theme.BG_DARK); self.prog.pack(fill="x", padx=20, pady=5); self.prog.set(0)

        # Preview
        self.preview_box = ctk.CTkFrame(content, fg_color=Theme.PANEL_BG, corner_radius=15)
        self.preview_box.grid(row=0, column=1, sticky="nsew"); self.preview_box.grid_rowconfigure(0, weight=1); self.preview_box.grid_columnconfigure(0, weight=1)
        self.pre_lbl = ctk.CTkLabel(self.preview_box, text="Preview Area", font=ctk.CTkFont(size=14), text_color=Theme.CARD_BG); self.pre_lbl.grid(row=0, column=0)

        bot = ctk.CTkFrame(self, height=40, fg_color="transparent")
        bot.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.status = ctk.CTkLabel(bot, text="Ready", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_DIM); self.status.pack(side="left")

    def _label(self, parent, txt):
        l = ctk.CTkLabel(parent, text=txt, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM, anchor="w")
        l.pack(fill="x", padx=15, pady=2); return l

    def select_video(self):
        p = filedialog.askopenfilename()
        if p:
            self.video_path = p; self.lbl_file.configure(text=f"📄 {os.path.basename(p)}", text_color=Theme.TEXT_MAIN)
            self.status.configure(text="Analyzing...", text_color=Theme.ACCENT); threading.Thread(target=self._probe, daemon=True).start()

    def _probe(self):
        info = FFmpegManager.probe_video(self.video_path)
        if info: self.video_info = info; self.after(0, self._apply_probe)

    def _apply_probe(self):
        self.lbl_res.configure(text=f"📐 {self.video_info['w']}x{self.video_info['h']}", text_color=Theme.TEXT_MAIN)
        self.extract_btn.configure(state="normal"); self.scrub_btn.configure(state="normal")
        self.status.configure(text="✅ Video Loaded", text_color=Theme.SUCCESS)

    def open_scrubber(self):
        """Extracts last 10 frames and shows a choice window."""
        win = ctk.CTkToplevel(self); win.title("AIVerse Timeline Scrubber"); win.geometry("1100x400")
        win.configure(fg_color=Theme.BG_DARK); win.transient(self); win.grab_set()
        
        ctk.CTkLabel(win, text="Timeline Scrubber - Select the Perfect Frame", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)
        scroll = ctk.CTkScrollableFrame(win, orientation="horizontal", fg_color=Theme.PANEL_BG, height=280)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        msg = ctk.CTkLabel(scroll, text="Decoding terminal frames... Please wait.", text_color=Theme.TEXT_DIM)
        msg.pack(pady=100)

        def decode():
            ff = FFmpegManager.get_ffmpeg(); folder = os.path.join(os.path.abspath("."), "tmp_scrubber")
            if os.path.exists(folder): shutil.rmtree(folder)
            os.makedirs(folder)
            
            # Extract last 10 frames at 2fps
            cmd = [ff, "-y", "-sseof", "-5", "-i", self.video_path, "-r", "2", "-vframes", "10", os.path.join(folder, "frame_%03d.jpg")]
            subprocess.run(cmd, capture_output=True)
            
            imgs = sorted([f for f in os.listdir(folder) if f.endswith(".jpg")])
            self.after(0, lambda: self._show_scrub_results(scroll, folder, imgs, win, msg))

        threading.Thread(target=decode, daemon=True).start()

    def _show_scrub_results(self, scroll, folder, files, win, msg):
        msg.destroy()
        for f in files:
            path = os.path.join(folder, f)
            img = Image.open(path); img.thumbnail((180, 120))
            ctk_img = ctk.CTkImage(img, size=(img.width, img.height))
            
            f_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            f_frame.pack(side="left", padx=10)
            
            btn = ctk.CTkButton(f_frame, image=ctk_img, text="", width=180, height=120, fg_color=Theme.CARD_BG,
                                command=lambda p=path: self._select_scrub_frame(p, win))
            btn.pack()
            ctk.CTkLabel(f_frame, text=f"Frame {f.split('_')[1].split('.')[0]}", font=ctk.CTkFont(size=10), text_color=Theme.TEXT_DIM).pack(pady=2)

    def _select_scrub_frame(self, path, win):
        # Create final folder and move
        folder = os.path.join(os.path.dirname(self.video_path), f"{os.path.splitext(os.path.basename(self.video_path))[0]}_Frames")
        os.makedirs(folder, exist_ok=True)
        final = os.path.join(folder, f"SelectedFrame_{int(time.time())}.png")
        
        img = Image.open(path)
        if self.sharp_var.get():
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            img = ImageEnhance.Contrast(img).enhance(1.1)
        img.save(final)
        
        win.destroy(); self._on_done(final)

    def extract(self):
        self.extract_btn.configure(state="disabled", text="⏳ ...")
        self.prog.set(0.4); threading.Thread(target=self._run_ffmpeg, daemon=True).start()

    def _run_ffmpeg(self):
        try:
            ff = FFmpegManager.get_ffmpeg()
            ext = ".png" if "PNG" in self.fmt_var.get() else ".jpg"
            folder = os.path.join(os.path.dirname(self.video_path), f"{os.path.splitext(os.path.basename(self.video_path))[0]}_Frames")
            os.makedirs(folder, exist_ok=True)
            out = os.path.join(folder, f"LastFrame_{int(time.time())}{ext}")
            
            # Optimized targeted seek for speed and reliability
            # Even for "True-Shot", we start at the end and seek precisely
            seek_point = max(0, self.video_info['dur'] - 0.5) 
            
            cmd = [ff, "-y", "-ss", str(seek_point), "-i", self.video_path, "-vframes", "1", out]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(out):
                if self.sharp_var.get():
                    with Image.open(out) as img:
                        enhanced = ImageEnhance.Sharpness(img).enhance(1.6)
                        enhanced = ImageEnhance.Contrast(enhanced).enhance(1.05)
                        enhanced.save(out)
                self.output_path = out
                self.after(0, lambda: self._on_done(out))
            else:
                error_msg = result.stderr if result.stderr else "Unknown FFmpeg error"
                self.after(0, lambda: self.status.configure(text="❌ Extraction Failed", text_color=Theme.ERROR))
                print(f"Extraction Error: {error_msg}")
        except Exception as e:
            self.after(0, lambda: self.status.configure(text=f"❌ Error: {str(e)}", text_color=Theme.ERROR))
            self.after(0, lambda: self.extract_btn.configure(state="normal", text="⚡ Extract Last Frame"))

    def _on_done(self, out):
        self.extract_btn.configure(state="normal", text="⚡ Extract Last Frame"); self.prog.set(1.0)
        self.status.configure(text=f"✅ Saved & Enhanced", text_color=Theme.SUCCESS)
        img = Image.open(out); img.thumbnail((600, 400)); ctk_img = ctk.CTkImage(img, size=(img.width, img.height))
        self.pre_lbl.configure(image=ctk_img, text=""); self.pre_lbl.image = ctk_img
        if SettingsManager.load().get("auto_open"): os.startfile(os.path.dirname(out))

# ─── View: Batch Extractor ────────────────────────────────────────────────
class BatchView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self._init_ui()

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        banner = ctk.CTkFrame(self, fg_color=Theme.PANEL_BG, corner_radius=15, height=100)
        banner.grid(row=0, column=0, sticky="ew", padx=20, pady=20); banner.grid_propagate(False)
        ctk.CTkLabel(banner, text="📦 BATCH PROCESSING SUITE", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.ACCENT).pack(pady=(15, 0))
        ctk.CTkLabel(banner, text="Automatically extract last frames from entire directories", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack()
        main = ctk.CTkFrame(self, fg_color="transparent"); main.grid(row=1, column=0, sticky="nsew", padx=20)
        main.grid_columnconfigure(0, weight=1); main.grid_rowconfigure(1, weight=1)
        input_f = ctk.CTkFrame(main, fg_color=Theme.PANEL_BG, corner_radius=12); input_f.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.path_label = ctk.CTkLabel(input_f, text="No folder selected...", text_color=Theme.TEXT_DIM); self.path_label.pack(side="left", padx=20, pady=15)
        ctk.CTkButton(input_f, text="📂 Select Folder", width=140, fg_color=Theme.ACCENT, command=self.select_dir).pack(side="right", padx=20)
        self.log_box = ctk.CTkTextbox(main, fg_color=Theme.PANEL_BG, corner_radius=12, text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=11))
        self.log_box.grid(row=1, column=0, sticky="nsew"); self.log_box.insert("0.0", ">>> Batch logs will appear here...\n")
        self.start_btn = ctk.CTkButton(self, text="🚀 START BATCH PROCESS", height=55, fg_color=Theme.SUCCESS, font=ctk.CTkFont(weight="bold"), state="disabled", command=self.start_batch)
        self.start_btn.grid(row=2, column=0, sticky="ew", padx=20, pady=20)

    def select_dir(self):
        d = filedialog.askdirectory()
        if d: self.dir = d; self.path_label.configure(text=f"📍 {d}", text_color=Theme.TEXT_MAIN); self.start_btn.configure(state="normal")

    def start_batch(self):
        self.start_btn.configure(state="disabled", text="⏳ Processing..."); threading.Thread(target=self._run_batch, daemon=True).start()

    def _run_batch(self):
        ff = FFmpegManager.get_ffmpeg(); files = [f for f in os.listdir(self.dir) if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))]
        self.log_box.insert("end", f"\n[Found {len(files)} videos. Beginning extraction...]\n")
        for i, filename in enumerate(files):
            path = os.path.join(self.dir, filename); self.log_box.insert("end", f"> Processing: {filename}...")
            info = FFmpegManager.probe_video(path)
            if info:
                folder = os.path.join(self.dir, "AIVerse_Batch_Output"); os.makedirs(folder, exist_ok=True)
                out = os.path.join(folder, f"{os.path.splitext(filename)[0]}_LastFrame.png")
                cmd = [ff, "-y", "-ss", str(max(0, info['dur']-1)), "-i", path, "-update", "1", "-vframes", "1", out]
                subprocess.run(cmd, capture_output=True); self.log_box.insert("end", " DONE\n")
            else: self.log_box.insert("end", " FAILED\n")
            self.log_box.see("end")
        self.log_box.insert("end", "\n[BATCH PROCESS COMPLETE]\n"); self.after(0, lambda: self.start_btn.configure(state="normal", text="🚀 START BATCH PROCESS"))
        if SettingsManager.load().get("auto_open"): os.startfile(os.path.join(self.dir, "AIVerse_Batch_Output"))

# ─── View: Storyboard ─────────────────────────────────────────────────────
class StoryboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.video_path = None
        self.frames_data = [] # List of {path, label, time}
        self._init_ui()

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        banner = ctk.CTkFrame(self, fg_color=Theme.PANEL_BG, corner_radius=15, height=100)
        banner.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        ctk.CTkLabel(banner, text="🎞️ CINEMATIC STORYBOARD", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.ACCENT).pack(pady=(15, 0))
        ctk.CTkLabel(banner, text="Extract and Download individual First, Middle, or Last frames", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack()

        # Workspace for frames
        self.work_area = ctk.CTkScrollableFrame(self, fg_color=Theme.PANEL_BG, corner_radius=15)
        self.work_area.grid(row=1, column=0, sticky="nsew", padx=20)
        
        self.placeholder = ctk.CTkLabel(self.work_area, text="Select a video to generate shots", text_color=Theme.CARD_BG)
        self.placeholder.pack(pady=100)

        ctrls = ctk.CTkFrame(self, fg_color="transparent")
        ctrls.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkButton(ctrls, text="📂 Select Video", command=self.select_video, fg_color=Theme.CARD_BG).pack(side="left", padx=10)
        self.gen_btn = ctk.CTkButton(ctrls, text="🎨 Generate All Frames", fg_color=Theme.SUCCESS, state="disabled", command=self.generate)
        self.gen_btn.pack(side="right", padx=10)

    def select_video(self):
        p = filedialog.askopenfilename()
        if p:
            self.video_path = p
            self.gen_btn.configure(state="normal")

    def generate(self):
        for child in self.work_area.winfo_children(): child.destroy()
        msg = ctk.CTkLabel(self.work_area, text="Processing Cinematic Frames...", text_color=Theme.TEXT_DIM)
        msg.pack(pady=100)
        self.gen_btn.configure(state="disabled", text="⏳ Rendering...")
        threading.Thread(target=self._run_gen, args=(msg,), daemon=True).start()

    def _run_gen(self, msg_lbl):
        ff = FFmpegManager.get_ffmpeg()
        info = FFmpegManager.probe_video(self.video_path)
        if not info: return

        folder = os.path.join(os.path.dirname(self.video_path), "AIVerse_Shots")
        os.makedirs(folder, exist_ok=True)
        
        # Target: Start, Middle, End
        targets = [
            {"label": "First Frame", "time": 0.5}, # Slightly offset to avoid absolute zero black
            {"label": "Middle Frame", "time": info['dur'] / 2},
            {"label": "Last Frame", "time": max(0, info['dur'] - 1)}
        ]
        
        results = []
        for i, target in enumerate(targets):
            out = os.path.join(folder, f"{target['label'].replace(' ', '')}_{int(time.time())}.png")
            cmd = [ff, "-y", "-ss", str(target['time']), "-i", self.video_path, "-vframes", "1", out]
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(out):
                results.append({"path": out, "label": target['label']})

        # Also create combined strip
        if len(results) == 3:
            strip_path = os.path.join(folder, f"FullStoryboard_{int(time.time())}.png")
            imgs = [Image.open(r["path"]) for r in results]
            total_w = sum(img.width for img in imgs)
            max_h = max(img.height for img in imgs)
            strip = Image.new('RGB', (total_w, max_h))
            x = 0
            for img in imgs:
                strip.paste(img, (x, 0))
                x += img.width
            strip.save(strip_path)
            results.append({"path": strip_path, "label": "Full Storyboard Strip"})

        self.after(0, lambda: self._on_done(results, msg_lbl))

    def _on_done(self, results, msg_lbl):
        msg_lbl.destroy()
        self.gen_btn.configure(state="normal", text="🎨 Generate All Frames")
        
        for res in results:
            card = ctk.CTkFrame(self.work_area, fg_color=Theme.CARD_BG, corner_radius=12)
            card.pack(fill="x", padx=15, pady=10)
            
            # Preview Left
            img = Image.open(res["path"])
            img.thumbnail((300, 200))
            ctk_img = ctk.CTkImage(img, size=(img.width, img.height))
            
            pre = ctk.CTkLabel(card, image=ctk_img, text="")
            pre.pack(side="left", padx=15, pady=15)
            
            # Details Center
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="y", padx=20, pady=20)
            ctk.CTkLabel(info, text=res["label"], font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
            ctk.CTkLabel(info, text=f"Captured from: {os.path.basename(self.video_path)}", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_DIM).pack(anchor="w")
            
            # Action Right
            def open_f(p=res["path"]): os.startfile(p)
            ctk.CTkButton(card, text="💾 Open & View", width=120, height=40, fg_color=Theme.ACCENT, command=open_f).pack(side="right", padx=20)

        if SettingsManager.load().get("auto_open") and results:
            os.startfile(os.path.dirname(results[0]["path"]))

# ─── Main Application ──────────────────────────────────────────────────────
class AIVerseStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AIVerseStudio - Creative Suite"); self.geometry("1300x850"); self.configure(fg_color=Theme.BG_DARK)
        self.current_view = None; self._init_ui(); self.switch_tab("home")

    def _init_ui(self):
        self.grid_columnconfigure(0, weight=0); self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.nav = ctk.CTkFrame(self, width=280, fg_color=Theme.PANEL_BG, corner_radius=0); self.nav.grid(row=0, column=0, sticky="nsew"); self.nav.grid_propagate(False)
        header = ctk.CTkFrame(self.nav, fg_color="transparent"); header.pack(fill="x", pady=30, padx=20)
        ctk.CTkLabel(header, text="🌌", font=ctk.CTkFont(size=40)).pack(); ctk.CTkLabel(header, text="AIVerseStudio", font=ctk.CTkFont(size=20, weight="bold")).pack()
        self.btns = {}
        self._nav_btn("home", "🏠  Dashboard", "home"); self._nav_btn("extract", "⚡  Single Extract", "extract")
        self._nav_btn("batch", "📦  Batch Suite", "batch"); self._nav_btn("story", "🎞️  Storyboard", "story")
        ctk.CTkFrame(self.nav, fg_color="transparent", height=100).pack(fill="y", expand=True)
        self._nav_btn("settings", "⚙️  Preferences", "settings")
        self.container = ctk.CTkFrame(self, fg_color="transparent"); self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1); self.container.grid_columnconfigure(0, weight=1)

    def _nav_btn(self, id, text, tab_name):
        btn = ctk.CTkButton(self.nav, text=text, height=50, corner_radius=10, anchor="w", fg_color="transparent", hover_color=Theme.CARD_BG, text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=13), command=lambda: self.switch_tab(tab_name))
        btn.pack(fill="x", padx=15, pady=5); self.btns[id] = btn

    def switch_tab(self, tab):
        if self.current_view: self.current_view.destroy()
        for k, v in self.btns.items(): v.configure(fg_color="transparent", text_color=Theme.TEXT_DIM)
        if tab == "home":
            self.current_view = HomeView(self.container, self); self.btns["home"].configure(fg_color=Theme.ACCENT, text_color="white")
        elif tab == "extract":
            self.current_view = SingleFrameView(self.container, self); self.btns["extract"].configure(fg_color=Theme.ACCENT, text_color="white")
        elif tab == "batch":
            self.current_view = BatchView(self.container, self); self.btns["batch"].configure(fg_color=Theme.ACCENT, text_color="white")
        elif tab == "story":
            self.current_view = StoryboardView(self.container, self); self.btns["story"].configure(fg_color=Theme.ACCENT, text_color="white")
        elif tab == "settings": self.show_settings(); return
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_settings(self):
        win = ctk.CTkToplevel(self); win.title("Preferences"); win.geometry("540x550"); win.configure(fg_color=Theme.BG_DARK); win.transient(self); win.grab_set()
        ctk.CTkLabel(win, text="⚙️ App Preferences", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        s = SettingsManager.load()
        container = ctk.CTkFrame(win, fg_color=Theme.PANEL_BG, corner_radius=15); container.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        f_ent = self._st_row(container, "FFmpeg Path", s["ffmpeg_path"]); p_ent = self._st_row(container, "FFprobe Path", s["ffprobe_path"])
        auto_var = tk.BooleanVar(value=s.get("auto_open", True)); ctk.CTkCheckBox(container, text="Auto-open folder after extraction", variable=auto_var, font=ctk.CTkFont(size=12), text_color=Theme.TEXT_DIM, border_color=Theme.ACCENT).pack(anchor="w", padx=30, pady=20)
        def save():
            SettingsManager.save({"ffmpeg_path": f_ent.get(), "ffprobe_path": p_ent.get(), "auto_open": auto_var.get()})
            win.destroy()
        ctk.CTkButton(win, text="💾 Save Preferences", height=45, fg_color=Theme.ACCENT, command=save).pack(pady=(0,30))

    def _st_row(self, master, lbl, val):
        f = ctk.CTkFrame(master, fg_color="transparent"); f.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(f, text=lbl, text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        e = ctk.CTkEntry(f, width=400, fg_color=Theme.BG_DARK); e.insert(0, val); e.pack(pady=5); return e

if __name__ == "__main__":
    app = AIVerseStudio(); app.mainloop()
