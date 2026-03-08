import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import json
import os
import threading
from PIL import Image, ImageTk
import shutil
import numpy as np

from scene_parser import ScriptParser
from vector_renderer import VectorRenderer
from storyboard_generator import StoryboardGenerator
from export_manager import ExportManager
import local_inpainter

SETTINGS_FILE = "settings.json"

# ─── Theme ─────────────────────────────────────────────────────────────────────
class Theme:
    ACCENT       = "#6366F1"
    SUCCESS      = "#10B981"
    ERROR        = "#EF4444"
    BG_DARK      = "#0F172A"
    PANEL_BG     = "#1E293B"
    CARD_BG      = "#334155"
    TEXT_MAIN    = "#F8FAFC"
    TEXT_DIM     = "#94A3B8"

# ─── Settings ──────────────────────────────────────────────────────────────────
class SettingsManager:
    DEFAULTS = {
        "ffmpeg_path":    r"C:\Users\srika\FFMeg\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
        "ffprobe_path":   r"C:\Users\srika\FFMeg\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffprobe.exe"
    }
    @classmethod
    def load(cls):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE) as f:
                    return {**cls.DEFAULTS, **json.load(f)}
            except: pass
        return cls.DEFAULTS.copy()

    @classmethod
    def save(cls, data):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)

# ─── FFmpeg ────────────────────────────────────────────────────────────────────
class FFmpegManager:
    @classmethod
    def get(cls, key="ffmpeg_path"):
        path = SettingsManager.load().get(key, "")
        return path if path and os.path.exists(path) else key.replace("_path","")
    @classmethod
    def probe(cls, path):
        try:
            cmd = [cls.get("ffprobe_path"), "-v", "quiet", "-print_format", "json",
                   "-show_streams", "-show_format", path]
            data = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
            v = next(s for s in data["streams"] if s["codec_type"] == "video")
            return {"w": v["width"], "h": v["height"], "dur": float(data["format"].get("duration", 0))}
        except: return None

# ═══════════════════════════════════════════════════════════════════════════════
# VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

class HomeView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self._build()
    def _build(self):
        hero = ctk.CTkFrame(self, fg_color=Theme.PANEL_BG, corner_radius=20)
        hero.pack(fill="x", padx=40, pady=40)
        ctk.CTkLabel(hero, text="🌌 AIVerseStudio Pro", font=ctk.CTkFont(size=32, weight="bold")).pack(pady=(30,5))
        ctk.CTkLabel(hero, text="Cinematic Script-to-Visual Storyboard Suite", text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=14)).pack(pady=(0,30))
        cards = ctk.CTkFrame(self, fg_color="transparent"); cards.pack(fill="x", padx=30)
        cards.grid_columnconfigure((0,1,2,3), weight=1)
        self._card(cards, "⚡", "Extract", "Single Frame", "extract", 0)
        self._card(cards, "📦", "Batch", "Full Folders", "batch", 1)
        self._card(cards, "🎞️", "Shot Board", "Video → Frames", "story", 2)
        self._card(cards, "📜", "Script Board", "Script → Storyboard", "script", 3)
        self._card(cards, "💧", "Eraser", "Remove Watermark", "watermark", 4)
        self._card(cards, "🎨", "Inpaint", "Image Eraser", "img_eraser", 5)
    def _card(self, m, icon, title, sub, tab, col):
        f = ctk.CTkFrame(m, fg_color=Theme.PANEL_BG, corner_radius=15, height=170)
        f.grid(row=0, column=col, padx=10, sticky="nsew"); f.grid_propagate(False)
        ctk.CTkLabel(f, text=icon, font=ctk.CTkFont(size=32)).pack(pady=(20,5))
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack()
        ctk.CTkLabel(f, text=sub, text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=11)).pack()
        ctk.CTkButton(f, text="Open →", height=30, fg_color=Theme.CARD_BG, command=lambda: self.app.switch_tab(tab)).pack(pady=15, padx=20, fill="x")

class SingleFrameView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.video_path = None; self._build()
    def _build(self):
        ctk.CTkLabel(self, text="⚡ SINGLE FRAME EXTRACTION", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.ACCENT).pack(pady=20)
        ctk.CTkButton(self, text="📂 Select Video", command=self.select, fg_color=Theme.ACCENT).pack(pady=10)
        self.pre = ctk.CTkLabel(self, text="No video selected", height=450, fg_color=Theme.PANEL_BG, corner_radius=15, text_color=Theme.TEXT_DIM)
        self.pre.pack(fill="both", expand=True, padx=40, pady=20)
        self.btn = ctk.CTkButton(self, text="Extract Last Frame", state="disabled", command=self.run, fg_color=Theme.SUCCESS, height=45)
        self.btn.pack(pady=20)
    def select(self):
        p = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.mov *.avi *.mkv")])
        if p: self.video_path = p; self.btn.configure(state="normal"); self.pre.configure(text=f"Loaded: {os.path.basename(p)}")
    def run(self):
        ff = FFmpegManager.get(); info = FFmpegManager.probe(self.video_path)
        if not info: messagebox.showerror("Error", "Cannot read video."); return
        base = os.path.splitext(os.path.basename(self.video_path))[0]
        out = os.path.join(os.path.dirname(self.video_path), f"{base}.png")
        subprocess.run([ff, "-y", "-ss", str(max(0, info['dur']-0.5)), "-i", self.video_path, "-vframes", "1", out], capture_output=True)
        if os.path.exists(out):
            img = Image.open(out); img.thumbnail((900, 500)); ci = ctk.CTkImage(img, size=(img.width, img.height))
            self.pre.configure(image=ci, text="")
            messagebox.showinfo("Success", f"Last Frame saved successfully!\nLocation: {out}")
        else:
            messagebox.showerror("Error", "Extraction failed. FFmpeg could not save the frame.")

class BatchView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self._build()
    def _build(self):
        ctk.CTkLabel(self, text="📦 BATCH PRODUCTION SUITE", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        self.log = ctk.CTkTextbox(self, fg_color=Theme.PANEL_BG, font=ctk.CTkFont(family="Courier", size=11), text_color="#a3e635")
        self.log.pack(fill="both", expand=True, padx=40, pady=10)
        ctk.CTkButton(self, text="📂 Select Folder & Process", command=self.start, fg_color=Theme.ACCENT, height=40).pack(pady=20)
    def start(self):
        d = filedialog.askdirectory()
        if d: threading.Thread(target=self._proc, args=(d,), daemon=True).start()
    def _proc(self, d):
        ff = FFmpegManager.get()
        files = [f for f in os.listdir(d) if f.lower().endswith(('.mp4','.mov','.avi'))]
        self.log.insert("end", f"Found {len(files)} videos...\n")
        for f in files:
            self.log.insert("end", f"  ⚙ {f}  "); out = os.path.join(d, f"{os.path.splitext(f)[0]}_End.png")
            subprocess.run([ff, "-y", "-sseof", "-1", "-i", os.path.join(d, f), "-vframes", "1", out], capture_output=True)
            self.log.insert("end", "✓\n")
        self.log.insert("end", "✅ Batch complete!\n")
        messagebox.showinfo("Success", f"Batch processing complete!\nFrames saved in: {d}")

class StoryboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self._build()
    def _build(self):
        ctk.CTkLabel(self, text="🎞️ VIDEO SHOT STORYBOARD", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        ctk.CTkButton(self, text="📂 Select Video", command=self.select, fg_color=Theme.ACCENT).pack()
        self.sc = ctk.CTkScrollableFrame(self, fg_color=Theme.PANEL_BG); self.sc.pack(fill="both", expand=True, padx=20, pady=20)
    def select(self):
        p = filedialog.askopenfilename()
        if p: threading.Thread(target=self._run, args=(p,), daemon=True).start()
    def _run(self, p):
        ff = FFmpegManager.get(); info = FFmpegManager.probe(p)
        if not info: return
        for t in [0.1, info['dur']/2, info['dur']-0.1]:
            out = os.path.join(os.path.dirname(p), f"shot_{t:.1f}.png")
            subprocess.run([ff, "-y", "-ss", str(t), "-i", p, "-vframes", "1", out], capture_output=True)
            img = Image.open(out); img.thumbnail((280, 160)); ci = ctk.CTkImage(img, size=(img.width, img.height))
            self.after(0, lambda i=ci: ctk.CTkLabel(self.sc, image=i, text="").pack(pady=5))

# ─── Watermark Remover View ────────────────────────────────────────────────────
class WatermarkRemoverView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.video_path = None
        self.video_info = None
        self.preview_image = None
        self.selection_rect = None
        self.start_x = None
        self.start_y = None
        self.x1, self.y1, self.x2, self.y2 = 0, 0, 0, 0
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 0))
        ctk.CTkLabel(header, text="💧 WATERMARK REMOVER", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.ACCENT).pack(side="left")
        ctk.CTkButton(header, text="📂 Select Video", command=self.select_video, fg_color=Theme.CARD_BG, width=120).pack(side="right")

        # Main Workspace
        self.work = ctk.CTkFrame(self, fg_color=Theme.PANEL_BG, corner_radius=15)
        self.work.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        
        # Canvas for selection
        self.canvas = tk.Canvas(self.work, bg="#0f172a", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # Controls
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        coords_f = ctk.CTkFrame(ctrl, fg_color="transparent")
        coords_f.pack(side="left")
        
        self.coords_lbl = ctk.CTkLabel(coords_f, text="Area: (0, 0) Size: 0x0", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_DIM)
        self.coords_lbl.pack(side="left", padx=10)

        self.proc_btn = ctk.CTkButton(ctrl, text="✨ REMOVE WATERMARK", command=self.process, fg_color=Theme.SUCCESS, state="disabled", font=ctk.CTkFont(weight="bold"))
        self.proc_btn.pack(side="right", padx=10)
        
        self.progress = ctk.CTkProgressBar(self, fg_color=Theme.CARD_BG, progress_color=Theme.ACCENT)
        self.progress.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.progress.set(0)

    def select_video(self):
        p = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.mov *.avi *.mkv")])
        if p:
            self.video_path = p
            self.video_info = FFmpegManager.probe(p)
            if self.video_info:
                self.load_preview()
                self.proc_btn.configure(state="normal")
            else:
                messagebox.showerror("Error", "Could not probe video.")

    def load_preview(self):
        ff = FFmpegManager.get()
        # Extract a frame from the middle
        t = self.video_info['dur'] / 2
        tmp_frame = "tmp_watermark_preview.png"
        subprocess.run([ff, "-y", "-ss", str(t), "-i", self.video_path, "-vframes", "1", tmp_frame], capture_output=True)
        
        if os.path.exists(tmp_frame):
            img = Image.open(tmp_frame)
            # Resize to fit canvas while maintaining aspect ratio
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw < 10 or ch < 10: # Canvas not yet rendered properly or too small
                cw, ch = 800, 450
            
            img.thumbnail((cw, ch))
            self.preview_image = ImageTk.PhotoImage(img)
            self.img_scale_w = self.video_info['w'] / img.width
            self.img_scale_h = self.video_info['h'] / img.height
            
            self.canvas.delete("all")
            self.canvas.create_image(cw//2, ch//2, image=self.preview_image, anchor="center")
            
            # Store image offsets for coordinate mapping
            self.img_offset_x = (cw - img.width) // 2
            self.img_offset_y = (ch - img.height) // 2
            
            os.remove(tmp_frame)

    def on_press(self, event):
        if not self.video_info: return
        self.start_x = event.x
        self.start_y = event.y
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        self.selection_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=Theme.ACCENT, width=2, dash=(4, 4))

    def on_drag(self, event):
        if not self.video_info or not self.selection_rect: return
        self.canvas.coords(self.selection_rect, self.start_x, self.start_y, event.x, event.y)
        self.update_coords(self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if not self.video_info: return
        self.x1, self.y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        self.x2, self.y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        self.update_coords(self.x1, self.y1, self.x2, self.y2)

    def update_coords(self, x1, y1, x2, y2):
        # Map back to video resolution
        vx1 = max(0, int((x1 - self.img_offset_x) * self.img_scale_w))
        vy1 = max(0, int((y1 - self.img_offset_y) * self.img_scale_h))
        vw = int((x2 - x1) * self.img_scale_w)
        vh = int((y2 - y1) * self.img_scale_h)
        self.coords_lbl.configure(text=f"Area: ({vx1}, {vy1}) Size: {vw}x{vh}")
        self.final_coords = (vx1, vy1, vw, vh)

    def process(self):
        if not hasattr(self, 'final_coords') or self.final_coords[2] <= 0:
            messagebox.showwarning("Selection", "Please select the watermark area first."); return
        
        out = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("Video","*.mp4")])
        if out:
            self.proc_btn.configure(state="disabled", text="⏳ Processing...")
            threading.Thread(target=self._run_ffmpeg, args=(out,), daemon=True).start()

    def _run_ffmpeg(self, out_path):
        ff = FFmpegManager.get()
        x, y, w, h = self.final_coords
        
        # PRO MODE: Sharp Patch Overlay (Avoids ugly delogo blur)
        self.after(0, lambda: self.proc_btn.configure(text="🪄 Initializing..."))
        try:
            # 1. Extract a sharp reference frame
            ref_frame = "tmp_vid_ref.png"
            subprocess.run([ff, "-y", "-ss", "0.5", "-i", self.video_path, "-vframes", "1", ref_frame], capture_output=True)
            
            if os.path.exists(ref_frame):
                # 2. Inpaint that frame with Professional Smooth engine
                img = Image.open(ref_frame)
                img = local_inpainter.professional_local_erase(img, x, y, x+w, y+h)
                
                # 3. Save the clean patch
                patch_file = "tmp_vid_patch.png"
                img.crop((x, y, x+w, y+h)).save(patch_file)
                
                # 4. Use overlay filter to paste the sharp patch over the whole video
                self.after(0, lambda: self.proc_btn.configure(text="🎞️ Rendering..."))
                cmd = [ff, "-y", "-i", self.video_path, "-i", patch_file, 
                       "-filter_complex", f"[0:v][1:v]overlay={x}:{y}", "-c:a", "copy", out_path]
                res = subprocess.run(cmd, capture_output=True, text=True)
                
                if res.returncode == 0:
                    self.after(0, lambda: messagebox.showinfo("Success", f"Sharp Removal complete!\n{out_path}"))
                    os.startfile(os.path.dirname(out_path))
                else:
                    raise Exception(f"FFmpeg Overlay Failed: {res.stderr[-200:]}")
            else:
                raise Exception("Cannot extract video frame.")
                
        except Exception as e:
            # Fallback to basic delogo if complex method fails
            cmd = [ff, "-y", "-i", self.video_path, "-vf", f"delogo=x={x}:y={y}:w={w}:h={h}", "-c:a", "copy", out_path]
            subprocess.run(cmd)
            self.after(0, lambda err=e: messagebox.showinfo("Completed", f"Basic removal complete.\n(Note: Sharp mode had issues: {str(err)})"))
            os.startfile(os.path.dirname(out_path))
            
        finally:
            for f in ["tmp_vid_ref.png", "tmp_vid_patch.png"]:
                if os.path.exists(f): os.remove(f)
            self._reset_proc_btn()

    def _reset_proc_btn(self):
        self.after(0, lambda: self.proc_btn.configure(state="normal", text="✨ REMOVE WATERMARK"))
        self.after(0, lambda: self.progress.set(0))

    def _reset_proc_btn(self):
        self.after(0, lambda: self.proc_btn.configure(state="normal", text="✨ REMOVE WATERMARK"))
        self.after(0, lambda: self.progress.set(0))

# ─── Image Eraser View ────────────────────────────────────────────────────────
class ImageEraserView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.image_path = None
        self.original_image = None
        self.display_image = None
        self.selection_rect = None
        self.start_x = None
        self.start_y = None
        self.x1, self.y1, self.x2, self.y2 = 0, 0, 0, 0
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 0))
        ctk.CTkLabel(header, text="🎨 IMAGE ERASER (INPAINT)", font=ctk.CTkFont(size=18, weight="bold"), text_color="#F472B6").pack(side="left")
        ctk.CTkButton(header, text="📂 Select Image", command=self.select_image, fg_color=Theme.CARD_BG, width=120).pack(side="right")

        # Main Workspace
        self.work = ctk.CTkFrame(self, fg_color=Theme.PANEL_BG, corner_radius=15)
        self.work.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        
        self.canvas = tk.Canvas(self.work, bg="#0f172a", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # Controls
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.coords_lbl = ctk.CTkLabel(ctrl, text="Select area to erase...", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_DIM)
        self.coords_lbl.pack(side="left", padx=10)

        self.proc_btn = ctk.CTkButton(ctrl, text="✨ ERASE SELECTION", command=self.process, fg_color="#DB2777", state="disabled", font=ctk.CTkFont(weight="bold"))
        self.proc_btn.pack(side="right", padx=10)

    def select_image(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if p:
            self.image_path = p
            self.original_image = Image.open(p)
            self.load_preview()
            self.proc_btn.configure(state="normal")

    def load_preview(self):
        if not self.original_image: return
        img = self.original_image.copy()
        
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10 or ch < 10: cw, ch = 800, 450
        
        img.thumbnail((cw, ch))
        self.display_image = ImageTk.PhotoImage(img)
        self.img_scale_w = self.original_image.width / img.width
        self.img_scale_h = self.original_image.height / img.height
        
        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, image=self.display_image, anchor="center")
        
        self.img_offset_x = (cw - img.width) // 2
        self.img_offset_y = (ch - img.height) // 2

    def on_press(self, event):
        if not self.original_image: return
        self.start_x = event.x
        self.start_y = event.y
        if self.selection_rect: self.canvas.delete(self.selection_rect)
        self.selection_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="#F472B6", width=2, dash=(4, 4))

    def on_drag(self, event):
        if not self.original_image or not self.selection_rect: return
        self.canvas.coords(self.selection_rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if not self.original_image: return
        self.x1, self.y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        self.x2, self.y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        
        # Map to real pixels
        rx1 = max(0, int((self.x1 - self.img_offset_x) * self.img_scale_w))
        ry1 = max(0, int((self.y1 - self.img_offset_y) * self.img_scale_h))
        rx2 = min(self.original_image.width, int((self.x2 - self.img_offset_x) * self.img_scale_w))
        ry2 = min(self.original_image.height, int((self.y2 - self.img_offset_y) * self.img_scale_h))
        
        self.final_rect = (rx1, ry1, rx2, ry2)
        self.coords_lbl.configure(text=f"Area: {rx2-rx1}x{ry2-ry1} at ({rx1}, {ry1})")

    def process(self):
        if not hasattr(self, 'final_rect') or (self.final_rect[2]-self.final_rect[0]) <= 0:
            messagebox.showwarning("Selection", "Please select an area first."); return
        
        out = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG (Alpha)","*.png"), ("JPEG","*.jpg")])
        if out:
            # PRO MODE: Texture-Sync Inpainting
            img = self.original_image.copy()
            x1, y1, x2, y2 = self.final_rect
            
            # Use high-quality local interpolation
            img = local_inpainter.professional_local_erase(img, x1, y1, x2, y2)
            
            if out.lower().endswith((".jpg", ".jpeg")):
                img.convert("RGB").save(out, quality=98)
            else:
                img.save(out)
                
            messagebox.showinfo("Success", f"Professional Sync complete!\nSaved to: {out}")
            os.startfile(os.path.dirname(out))

# ─── Script Storyboard View ────────────────────────────────────────────────────
class ScriptStoryboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.gen = StoryboardGenerator()
        self.scenes = []; self.svgs = []; self.pngs = []; self.idx = 0
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)

        # ── LEFT: Input ───────────────────────────────────────────────────────
        L = ctk.CTkFrame(self, fg_color=Theme.PANEL_BG, corner_radius=15)
        L.grid(row=0, column=0, sticky="nsew", padx=(0,8))

        ctk.CTkLabel(L, text="📜 SCRIPT INPUT", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.ACCENT).pack(pady=(15,5), padx=20, anchor="w")
        
        # Script text box — HIGH VISIBILITY
        self.txt = ctk.CTkTextbox(L, font=ctk.CTkFont(family="Courier New", size=13),
                                  fg_color="#070d1a", text_color="#f1f5f9", border_width=1, border_color=Theme.CARD_BG)
        self.txt.pack(fill="both", expand=True, padx=20, pady=5)
        self.txt.insert("1.0", 
            "SCENE 1 – The Flash\n\n"
            "Wide shot — futuristic city skyline.\n\n"
            "NEWS BROADCAST (V.O.)\n"
            "\"We are receiving reports of multiple launches—\"\n\n"
            "A blinding white flash consumes the skyline.\n\nSILENCE.\n\n"
            "Shockwave tears through buildings.\n\nCut to black.\n\n"
            "TEXT ON SCREEN: Year 2057."
        )

        # Controls row
        ctrl = ctk.CTkFrame(L, fg_color="transparent"); ctrl.pack(fill="x", padx=20, pady=10)
        self.style_var = ctk.StringVar(value="Cinematic Realistic")
        self.style_menu = ctk.CTkOptionMenu(ctrl,
            values=["Cinematic Realistic", "Pencil Sketch", "Comic Book", "Film Noir", "Anime Style"],
            variable=self.style_var, fg_color=Theme.CARD_BG, text_color="white",
            command=self._on_style_change, width=210)
        self.style_menu.pack(side="left", padx=(0,10))
        
        self.gen_btn = ctk.CTkButton(ctrl, text="🎬 GENERATE", command=self._on_generate,
                                     fg_color=Theme.SUCCESS, font=ctk.CTkFont(size=13, weight="bold"), height=38)
        self.gen_btn.pack(side="right")

        # Progress bar
        self.progress = ctk.CTkProgressBar(L, fg_color=Theme.CARD_BG, progress_color=Theme.ACCENT)
        self.progress.pack(fill="x", padx=20, pady=(0,10))
        self.progress.set(0)
        self.status_lbl = ctk.CTkLabel(L, text="Ready. Paste your script and click Generate.", 
                                        text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=11))
        self.status_lbl.pack(padx=20, pady=(0,10), anchor="w")

        # ── RIGHT: Preview ────────────────────────────────────────────────────
        R = ctk.CTkFrame(self, fg_color=Theme.PANEL_BG, corner_radius=15)
        R.grid(row=0, column=1, sticky="nsew", padx=(8,0))

        # Sub-panel for Card Preview (With Scroll)
        self.preview_container = ctk.CTkScrollableFrame(R, fg_color="#020617", corner_radius=10, height=450)
        self.preview_container.pack(fill="both", expand=True, padx=15, pady=(15,8))

        self.img_label = ctk.CTkLabel(self.preview_container, text="🎬 Preview will appear here",
                                       fg_color="transparent", text_color=Theme.TEXT_DIM, font=ctk.CTkFont(size=13))
        self.img_label.pack(fill="both", expand=True, pady=10)

        self.scene_title = ctk.CTkLabel(R, text="—", font=ctk.CTkFont(size=15, weight="bold"),
                                         text_color=Theme.ACCENT, anchor="w")
        self.scene_title.pack(fill="x", padx=20)

        self.scene_meta = ctk.CTkLabel(R, text="", font=ctk.CTkFont(size=11),
                                        text_color="#CBD5E1", anchor="w")
        self.scene_meta.pack(fill="x", padx=20, pady=(2,6))

        # Navigation
        nav = ctk.CTkFrame(R, fg_color="transparent"); nav.pack(pady=5)
        ctk.CTkButton(nav, text="◀", width=45, command=self.prev_scene).pack(side="left", padx=4)
        self.counter = ctk.CTkLabel(nav, text="0 / 0", font=ctk.CTkFont(size=13), text_color="white", width=80)
        self.counter.pack(side="left", padx=8)
        ctk.CTkButton(nav, text="▶", width=45, command=self.next_scene).pack(side="left", padx=4)

        # Export buttons
        expo = ctk.CTkFrame(R, fg_color="transparent"); expo.pack(side="bottom", fill="x", padx=15, pady=15)
        self.pdf_btn  = ctk.CTkButton(expo, text="📄 PDF",  command=self.exp_pdf,  fg_color=Theme.ACCENT, state="disabled")
        self.pptx_btn = ctk.CTkButton(expo, text="📊 PPTX", command=self.exp_pptx, fg_color=Theme.ACCENT, state="disabled")
        self.svg_btn  = ctk.CTkButton(expo, text="🗂 Folder", command=self.exp_folder, fg_color=Theme.CARD_BG, state="disabled")
        self.strip_btn= ctk.CTkButton(expo, text="🗞 Strip Sheet", command=self.exp_strip, fg_color="#7C3AED", state="disabled")
        for b in [self.pdf_btn, self.pptx_btn, self.svg_btn, self.strip_btn]:
            b.pack(side="left", padx=4, expand=True, fill="x")

    # ─── API Key ───────────────────────────────────────────────────────────────
    def _save_key(self):
        s = SettingsManager.load()
        s["gemini_api_key"] = self.api_key_var.get().strip()
        SettingsManager.save(s)
        self.api_status.configure(text="✓ Saved", text_color=Theme.SUCCESS)
        self.after(3000, lambda: self.api_status.configure(text=""))

    def _on_style_change(self, _=None):
        """Clear preview when style changes."""
        self.img_label.configure(image=None, text=f"Style: {self.style_var.get()}\nGenerate to preview.", text_color=Theme.TEXT_DIM)
        self.scene_title.configure(text="—")
        self.scene_meta.configure(text="")

    # ─── Generate ─────────────────────────────────────────────────────────────
    def _on_generate(self):
        script = self.txt.get("1.0", "end").strip()
        if not script:
            messagebox.showwarning("Empty Script", "Please paste your script first."); return
        self.gen_btn.configure(state="disabled", text="⏳ Generating...")
        self.progress.set(0)
        self.status_lbl.configure(text="Parsing scenes...")
        threading.Thread(target=self._do_generate, args=(script,), daemon=True).start()

    def _do_generate(self, script):
        def progress_cb(done, total):
            if total > 0:
                frac = done / total
                self.after(0, lambda: self.progress.set(frac))
                key = SettingsManager.load().get("gemini_api_key","")
                mode = "Gemini AI" if key else "Sketch"
                self.after(0, lambda: self.status_lbl.configure(
                    text=f"[{mode}] Generating scene {done}/{total}..."))

        try:
            scenes, svgs, pngs = self.gen.process_script(script, self.style_var.get(), progress_cb)
            self.scenes = scenes; self.svgs = svgs; self.pngs = pngs; self.idx = 0
            self.after(0, self._after_generate)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.gen_btn.configure(state="normal", text="🎬 GENERATE"))

    def _after_generate(self):
        self.gen_btn.configure(state="normal", text="🎬 GENERATE")
        self.progress.set(1)
        self.status_lbl.configure(text=f"✅ {len(self.scenes)} scenes generated!", text_color=Theme.SUCCESS)
        for b in [self.pdf_btn, self.pptx_btn, self.svg_btn, self.strip_btn]:
            b.configure(state="normal")
        self._show_scene()

    # ─── Preview ──────────────────────────────────────────────────────────────
    def _show_scene(self):
        if not self.scenes: return
        sc = self.scenes[self.idx]
        pn = self.pngs[self.idx]
        self.scene_title.configure(text=f"SCENE {self.idx+1}:  {sc.header}")
        self.scene_meta.configure(text=f"🎥 {sc.shot_type}   |   💡 {sc.lighting}   |   🎬 {sc.camera_movement}")
        self.counter.configure(text=f"{self.idx+1} / {len(self.scenes)}")

        # Clear old image first
        self.img_label.configure(image=None, text="Loading...", text_color=Theme.TEXT_DIM)
        self.update_idletasks()

        if pn and os.path.exists(pn):
            img = Image.open(pn)
            # Full vertical card scaling
            w_scaled = 450
            h_scaled = int(img.height * (450/img.width))
            ci = ctk.CTkImage(img, size=(w_scaled, h_scaled))
            self.img_label.configure(image=ci, text="")
            self._current_image = ci
        else:
            self.img_label.configure(image=None, text="⚠ Image not found", text_color=Theme.ERROR)

    def prev_scene(self):
        if self.idx > 0: self.idx -= 1; self._show_scene()
    def next_scene(self):
        if self.idx < len(self.scenes)-1: self.idx += 1; self._show_scene()

    # ─── Export ───────────────────────────────────────────────────────────────
    def exp_pdf(self):
        p = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF","*.pdf")])
        if p: ExportManager.export_as_pdf(self.scenes, self.svgs, p); os.startfile(p)
    def exp_pptx(self):
        p = filedialog.asksaveasfilename(defaultextension=".pptx", filetypes=[("PowerPoint","*.pptx")])
        if p: ExportManager.export_as_pptx(self.scenes, self.pngs, p); os.startfile(p)
    def exp_folder(self):
        os.startfile(os.path.abspath(self.gen.svg_dir))
    def exp_strip(self):
        p = os.path.abspath(os.path.join(self.gen.svg_dir, "storyboard_sheet.png"))
        if os.path.exists(p): os.startfile(p)
        else: messagebox.showinfo("Info", "Strip sheet not found.")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════
class AIVerseStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AIVerseStudio Pro  –  Cinematic Storyboard Suite")
        self.geometry("1440x900")
        self.configure(fg_color=Theme.BG_DARK)
        self.views = {}
        self._build_nav()
        self._build_views()
        self.switch_tab("home")

    def _build_nav(self):
        self.grid_columnconfigure(0, weight=0); self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        nav = ctk.CTkFrame(self, width=250, fg_color=Theme.PANEL_BG, corner_radius=0)
        nav.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(nav, text="🌌 AIVerseStudio", font=ctk.CTkFont(size=19, weight="bold")).pack(pady=(30,5))
        ctk.CTkLabel(nav, text="Pro Edition", text_color=Theme.ACCENT, font=ctk.CTkFont(size=11)).pack(pady=(0,25))
        self.btns = {}
        for tab_id, label in [("home","🏠  Dashboard"), ("script","📜  Script Board"),
                               ("extract","⚡  Frame Extract"), ("batch","📦  Batch Suite"), 
                               ("story","🎞️  Shot Board"), ("watermark", "💧  Watermark Remover"),
                               ("img_eraser", "🎨  Image Eraser")]:
            b = ctk.CTkButton(nav, text=label, height=46, anchor="w", fg_color="transparent",
                              text_color=Theme.TEXT_DIM, hover_color=Theme.CARD_BG,
                              command=lambda t=tab_id: self.switch_tab(t))
            b.pack(fill="x", padx=12, pady=3)
            self.btns[tab_id] = b

    def _build_views(self):
        self.cont = ctk.CTkFrame(self, fg_color="transparent")
        self.cont.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        self.cont.grid_rowconfigure(0, weight=1); self.cont.grid_columnconfigure(0, weight=1)
        for k, cls in [("home", HomeView), ("extract", SingleFrameView), ("batch", BatchView),
                       ("story", StoryboardView), ("script", ScriptStoryboardView),
                       ("watermark", WatermarkRemoverView), ("img_eraser", ImageEraserView)]:
            self.views[k] = cls(self.cont, self)

    def switch_tab(self, tab):
        for k, b in self.btns.items():
            b.configure(fg_color=Theme.ACCENT if k==tab else "transparent",
                        text_color="white" if k==tab else Theme.TEXT_DIM)
        for k, v in self.views.items():
            (v.grid(row=0, column=0, sticky="nsew") if k==tab else v.grid_forget())

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    AIVerseStudio().mainloop()
