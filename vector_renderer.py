"""
Masterpiece Storyboard Engine — Boords-Style Finals
Finalized Professional Manga Art with Screentone textures.
"""
import os, math, random, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

CW, CH = 640, 840   # Card Dimensions
FW, FH = 600, 338   # Frame Dimensions (16:9)
MARGIN = 20

def _font(size, bold=False):
    names = ["arialbd.ttf", "Arial Bold.ttf", "arial.ttf"] if bold else ["arial.ttf", "Arial.ttf"]
    for n in names:
        try: return ImageFont.truetype(n, size)
        except: pass
    return ImageFont.load_default()

class VectorRenderer:
    def __init__(self, output_dir="output_svg"):
        self.output_dir = output_dir
        self.panel_dir = os.path.join(output_dir, "panels")
        os.makedirs(self.panel_dir, exist_ok=True)
        self.all_panels = []

    def render_scene(self, scene, style_name, idx):
        card = Image.new("RGB", (CW, CH), (255, 255, 255))
        draw = ImageDraw.Draw(card, "RGBA")
        
        # 1. Header
        self._draw_header(draw, scene, idx)
        
        # 2. Cinematic Art Frame
        frame_img = self._render_frame(scene)
        card.paste(frame_img, (MARGIN, 80))
        
        # 3. Footer Text Blocks
        self._draw_footer(draw, scene)
        
        # 4. Master Card Border
        draw.rectangle([0, 0, CW-1, CH-1], outline=(220, 220, 220), width=1)
        
        # Save Outputs
        png_path = os.path.join(self.panel_dir, f"panel_{idx+1}.png")
        card.save(png_path, quality=97)
        preview_png = os.path.join(self.output_dir, f"scene_{idx+1}.png")
        card.save(preview_png)
        
        svg_path = os.path.join(self.output_dir, f"scene_{idx+1}.svg")
        with open(svg_path, "w") as f:
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}"><image href="{os.path.basename(preview_png)}" width="{CW}" height="{CH}"/></svg>')
            
        self.all_panels.append(card)
        return svg_path, preview_png

    def _draw_header(self, draw, scene, idx):
        draw.text((MARGIN, 25), f"SCENE {idx+1}", fill=(140, 140, 145), font=_font(12, True))
        draw.text((MARGIN, 45), scene.header.upper(), fill=(0, 0, 0), font=_font(16, True))
        
        # Type Indicator Pill
        tag_x = CW - 130
        draw.rounded_rectangle([tag_x, 30, tag_x+110, 55], radius=12, fill=(245, 245, 250))
        draw.text((tag_x+18, 36), scene.shot_type.split()[0], fill=(120, 130, 160), font=_font(11, True))

    def _render_frame(self, scene):
        frame = Image.new("RGB", (FW, FH), (255, 255, 255))
        draw = ImageDraw.Draw(frame, "RGBA")
        text = (scene.action + " " + scene.header).upper()

        # Screentone Background Sky
        for x in range(0, FW, 12):
            for y in range(0, 240, 12):
                draw.ellipse([x, y, x+3, y+3], fill=(220, 220, 230))
        
        # Ground
        draw.rectangle([0, FH-80, FW, FH], fill=(10, 10, 10))
        
        # Scenery Elements
        if "CAGE" in text or "GROVE" in text:
            for i in range(-1, 2):
                tx = FW//2 + i*180
                draw.line([(tx, FH-80), (tx, 20)], fill=(0,0,0), width=6)
                if i == 0: # Suspended cage
                    draw.rectangle([tx-35, 40, tx+35, 160], outline=(0,0,0), width=3)
                    for l in range(5):
                        draw.line([(tx-35+l*14, 40), (tx-35+l*14, 160)], fill=(0,0,0), width=1)
        
        # Multi-Character Confrontation
        speakers = sorted(list(set([d[0].upper() for d in scene.dialogue])))
        if len(speakers) >= 2:
            self._draw_manga_char(draw, 140, FH-50, scale=0.8, name=speakers[0])
            self._draw_manga_char(draw, FW-140, FH-50, scale=0.8, name=speakers[1], flip=True)
        else:
            self._draw_manga_char(draw, FW//2, FH-30, scale=1.0)
            
        return frame

    def _draw_manga_char(self, draw, cx, cy, scale=1.0, name="", flip=False):
        s = scale
        dir = -1 if flip else 1
        col = (0, 0, 0)
        
        # Spiky Gojo Hair
        h_pts = [(cx-35*s*dir, cy-110*s), (cx-50*s*dir, cy-140*s), (cx-20*s*dir, cy-125*s),
                 (cx, cy-175*s), (cx+20*s*dir, cy-125*s), (cx+50*s*dir, cy-140*s), (cx+35*s*dir, cy-110*s)]
        draw.polygon(h_pts, fill=(255,255,255), outline=col, width=3)
        
        # Sharp V-Jaw
        j_pts = [(cx-32*s*dir, cy-115*s), (cx, cy-65*s), (cx+32*s*dir, cy-115*s)]
        draw.polygon(j_pts, fill=(255,255,255), outline=col, width=3)
        
        # Intensity Eyes
        ex1, ex2 = sorted([cx-16*s*dir, cx-8*s*dir])
        ex3, ex4 = sorted([cx+8*s*dir, cx+16*s*dir])
        draw.line([(cx-22*s*dir, cy-95*s), (cx-5*s*dir, cy-93*s)], fill=col, width=4)
        draw.line([(cx+22*s*dir, cy-95*s), (cx+5*s*dir, cy-93*s)], fill=col, width=4)
        draw.ellipse([ex1, cy-88*s, ex2, cy-82*s], fill=(56, 189, 248), outline=col)
        draw.ellipse([ex3, cy-88*s, ex4, cy-82*s], fill=(56, 189, 248), outline=col)
        
        # Body (Jacket)
        b_pts = [(cx-55*s*dir, cy-65*s), (cx-65*s*dir, cy+180*s), (cx+65*s*dir, cy+180*s), (cx+55*s*dir, cy-65*s)]
        draw.polygon(b_pts, fill=col, outline=(40, 40, 40), width=1)
        # Collar Screentone (diagonal lines)
        for i in range(4):
            draw.line([(cx-10*s*dir, cy-55*s+i*4), (cx+10*s*dir, cy-55*s+i*(4 if not flip else -4))], fill=(100,100,100))

    def _draw_footer(self, draw, scene):
        f_lbl = _font(11, bold=True)
        f_txt = _font(13)
        
        # Action Block
        draw.text((MARGIN, 450), "ACTION", fill=(160, 160, 165), font=f_lbl)
        act = textwrap.fill(scene.action, width=82)
        draw.text((MARGIN, 470), act, fill=(30, 30, 30), font=f_txt)
        
        # Dialogue Block
        if scene.dialogue:
            draw.text((MARGIN, 650), "DIALOGUE", fill=(160, 160, 165), font=f_lbl)
            y = 675
            for speaker, speech in scene.dialogue[:2]:
                draw.text((MARGIN, y), f"{speaker}:", fill=(0, 0, 0), font=_font(12, True))
                y += 20
                swp = textwrap.fill(f'"{speech}"', width=74)
                draw.text((MARGIN+15, y), swp, fill=(50, 50, 50), font=f_txt)
                y += len(swp.split("\n")) * 18 + 12

    def build_strip_sheet(self, title="MANGA PRODUCTION — MASTERPIECE"):
        out = os.path.join(self.output_dir, "storyboard_sheet.png")
        if not self.all_panels: return ""
        cols = 2
        rows = math.ceil(len(self.all_panels) / cols)
        sheet_w = (CW + 40) * cols
        sheet_h = rows * (CH + 40) + 120
        sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 245))
        draw = ImageDraw.Draw(sheet)
        draw.text((40, 35), title, fill=(0, 0, 0), font=_font(38, True))
        for i, p in enumerate(self.all_panels):
            x = 40 + (i % cols) * (CW + 40)
            y = 120 + (i // cols) * (CH + 40)
            sheet.paste(p, (x, y))
        sheet.save(out)
        return out
