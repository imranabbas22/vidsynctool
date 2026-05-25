import os
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

THUMB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thumbnails")
os.makedirs(THUMB_DIR, exist_ok=True)

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
os.makedirs(FONT_DIR, exist_ok=True)

FONT_URL = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Bold.ttf"
FONT_PATH = os.path.join(FONT_DIR, "Montserrat-Bold.ttf")

if not os.path.exists(FONT_PATH):
    import urllib.request
    try:
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    except Exception:
        FONT_PATH = "C:\\Windows\\Fonts\\arialbd.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


NIGHT_DAY = {
    "myth_tint": (15, 10, 35),
    "myth_tint_strength": 0.55,
    "myth_desaturate": 0.60,
    "myth_darken": 0.50,
    "myth_glow": (150, 60, 100),
    "truth_tint": (200, 230, 255),
    "truth_tint_strength": 0.15,
    "truth_brighten": 0.15,
    "truth_glow": (100, 180, 255),
    "title_fill": (255, 255, 255),
    "title_outline": (10, 10, 30),
    "title_glow": (200, 220, 255),
}


class ThumbnailDesigner:

    def __init__(self, width=1080, height=1920):
        self.w = width
        self.h = height

    def _load_font(self, size):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            return ImageFont.load_default()

    def _resize_to_fill(self, img, target_w, target_h):
        """Resize image to fill target dimensions, cropping excess."""
        w, h = img.size
        target_ratio = target_w / target_h
        img_ratio = w / h
        if img_ratio > target_ratio:
            new_h = target_h
            new_w = int(w * (target_h / h))
        else:
            new_w = target_w
            new_h = int(h * (target_w / w))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        return img.crop((left, top, left + target_w, top + target_h))

    def _apply_color_grade(self, img, tint, tint_strength, desaturate=0, darken=0, brighten=0):
        """Apply color grading (tint, desaturation, brightness adjustment) to an image."""
        arr = np.array(img, dtype=np.float32)
        if desaturate > 0:
            gray = np.mean(arr, axis=2, keepdims=True)
            arr = arr * (1 - desaturate) + gray * desaturate
        if tint_strength > 0:
            tint_arr = np.array(tint, dtype=np.float32).reshape((1, 1, 3))
            arr = arr * (1 - tint_strength) + tint_arr * tint_strength
        if darken > 0:
            arr = arr * (1 - darken)
        if brighten > 0:
            arr = arr + (255 - arr) * brighten
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    def _build_diagonal_mask(self):
        """Build a binary mask: True for pixels in the top-left triangle (MYTH side)."""
        mask = np.zeros((self.h, self.w), dtype=bool)
        for y in range(self.h):
            x_boundary = int(self.w * (1 - y / self.h))
            mask[y, :x_boundary] = True
        return mask

    def _composite_diagonal(self, img_myth, img_truth):
        """Composite two images along the diagonal split (top-left = myth, bottom-right = truth)."""
        myth_arr = np.array(img_myth, dtype=np.uint8)
        truth_arr = np.array(img_truth, dtype=np.uint8)
        mask = self._build_diagonal_mask()
        result = np.where(mask[:, :, None], myth_arr, truth_arr)
        return Image.fromarray(result)

    def _draw_noise(self, img, count=6000, intensity=20):
        pixels = img.load()
        for _ in range(count):
            x = random.randint(0, self.w - 1)
            y = random.randint(0, self.h - 1)
            p = pixels[x, y]
            noise = random.randint(-intensity, intensity)
            pixels[x, y] = (
                max(0, min(255, p[0] + noise)),
                max(0, min(255, p[1] + noise)),
                max(0, min(255, p[2] + noise)),
            )

    def _draw_vignette(self, img, strength=0.50):
        """Dark vignette using radial gradient overlay."""
        w, h = img.size
        cx, cy = w // 2, h // 2
        max_dist = math.sqrt(cx**2 + cy**2)
        arr = np.array(img, dtype=np.float32)
        yy, xx = np.meshgrid(range(h), range(w), indexing="ij")
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        factor = np.clip(dist / max_dist * 1.6, 0, 1) ** 1.5
        factor = factor[:, :, None] * strength
        arr = arr * (1 - factor)
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    def _draw_seam_line(self, draw):
        w, h = self.w, self.h
        steps = max(w, h)
        seam_pts = [(int(w * i / steps), int(h * i / steps)) for i in range(steps + 1)]
        for i in range(len(seam_pts) - 1):
            x1, y1 = seam_pts[i]
            x2, y2 = seam_pts[i + 1]
            draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255), width=2)
            draw.line([(x1 + 1, y1 - 1), (x2 + 1, y2 - 1)], fill=(0, 180, 255), width=1)
        dash_len = 18
        gap_len = 14
        idx = 0
        toggle = 0
        while idx < len(seam_pts) - 1:
            end = min(idx + dash_len, len(seam_pts) - 1)
            if toggle == 0:
                draw.line([seam_pts[idx], seam_pts[end]], fill=(255, 255, 255), width=4)
            idx += dash_len + gap_len
            toggle ^= 1

    def _draw_side_labels(self, draw):
        s = NIGHT_DAY
        x_left = self.w // 10
        y_top = self.h // 18
        icon_font = self._load_font(int(self.w * 0.08))
        label_font = self._load_font(int(self.w * 0.025))
        draw.text((x_left, y_top), "\u274C", fill=s["myth_glow"] + (200,), font=icon_font)
        lw = draw.textlength("MYTH", font=label_font)
        draw.text((x_left - lw // 2 + int(self.w * 0.04), y_top + int(self.w * 0.09)), "MYTH", fill=s["myth_glow"] + (180,), font=label_font)
        check_size = draw.textlength("\u2705", font=icon_font)
        rx = self.w - x_left - int(check_size)
        ry = self.h - y_top - int(self.w * 0.14)
        draw.text((rx, ry), "\u2705", fill=s["truth_glow"] + (200,), font=icon_font)
        lw2 = draw.textlength("TRUTH", font=label_font)
        draw.text((rx - lw2 // 2 + int(check_size // 2), ry + int(self.w * 0.09)), "TRUTH", fill=s["truth_glow"] + (180,), font=label_font)

    def _draw_center_title(self, draw, title_text):
        s = NIGHT_DAY
        max_chars = 25
        if len(title_text) > max_chars:
            title_text = title_text[:max_chars].rsplit(" ", 1)[0] + "..."

        font_size = int(self.w * 0.058)
        if len(title_text) > 15:
            font_size = int(self.w * 0.048)
        elif len(title_text) > 10:
            font_size = int(self.w * 0.052)
        font = self._load_font(font_size)

        lines = []
        words = title_text.split()
        current_line = []
        max_text_w = int(self.w * 0.78)
        for word in words:
            test = " ".join(current_line + [word])
            if draw.textlength(test, font=font) <= max_text_w:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        line_height = font_size + 10
        total_h = len(lines) * line_height
        start_y = self.h // 2 - total_h // 2 - self.h // 30

        for line in lines:
            lw = draw.textlength(line, font=font)
            x = (self.w - lw) // 2
            y = start_y
            glow_r = max(2, font_size // 14)
            for dx in range(-glow_r, glow_r + 1):
                for dy in range(-glow_r, glow_r + 1):
                    if math.sqrt(dx**2 + dy**2) <= glow_r:
                        draw.text((x + dx, y + dy), line, fill=s["title_glow"] + (50,), font=font)
            outline_w = max(2, font_size // 20)
            for dx in range(-outline_w, outline_w + 1):
                for dy in range(-outline_w, outline_w + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), line, fill=s["title_outline"] + (255,), font=font)
            draw.text((x, y), line, fill=s["title_fill"] + (255,), font=font)
            mid_x = x + lw // 2
            mid_y = y + line_height // 2
            for r in range(10, 50, 10):
                alpha = max(0, 40 - r)
                draw.ellipse(
                    [(mid_x - r, mid_y - r), (mid_x + r, mid_y + r)],
                    outline=s["title_glow"] + (alpha,),
                    width=1,
                )
            start_y += line_height

    def _draw_channel_logo(self, draw):
        logo_size = int(min(self.w, self.h) * 0.065)
        logo_x = self.w - logo_size - int(self.w * 0.035)
        logo_y = self.h - logo_size - int(self.h * 0.035)
        draw.ellipse(
            [(logo_x, logo_y), (logo_x + logo_size, logo_y + logo_size)],
            fill=(0, 0, 0, 180),
            outline=(255, 215, 0),
            width=2,
        )
        logo_font = self._load_font(int(logo_size * 0.45))
        lw = draw.textlength("TDA", font=logo_font)
        draw.text(
            (logo_x + (logo_size - lw) // 2, logo_y + int(logo_size * 0.28)),
            "TDA", fill=(255, 215, 0), font=logo_font,
        )
        sub_font = self._load_font(int(logo_size * 0.18))
        sw = draw.textlength("AUDIT", font=sub_font)
        draw.text(
            (logo_x + (logo_size - sw) // 2, logo_y + int(logo_size * 0.62)),
            "AUDIT", fill=(200, 200, 200), font=sub_font,
        )

    def _draw_stamps(self, draw):
        pad = int(self.w * 0.018)
        bh = int(self.w * 0.048)
        stamp_font = self._load_font(int(self.w * 0.030))
        s1 = "FACT CHECKED"
        sw1 = draw.textlength(s1, font=stamp_font)
        sx1 = int(self.w * 0.035)
        sy1 = int(self.h * 0.58)
        draw.rounded_rectangle(
            [sx1, sy1, sx1 + int(sw1) + pad * 2, sy1 + bh],
            radius=4, fill=(220, 40, 40, 200),
        )
        draw.text((sx1 + pad, sy1 + int(bh * 0.15)), s1, fill=(255, 255, 255), font=stamp_font)
        s2 = "VERIFIED"
        sw2 = draw.textlength(s2, font=stamp_font)
        stamp_img = Image.new("RGBA", (int(sw2) + pad * 2, bh), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp_img)
        sd.rounded_rectangle([0, 0, stamp_img.width, stamp_img.height], radius=4, fill=(0, 160, 80, 180))
        sd.text((pad, int(bh * 0.15)), s2, fill=(255, 255, 255), font=stamp_font)
        rotated = stamp_img.rotate(-18, expand=True, resample=Image.Resampling.BICUBIC)
        sx2 = int(self.w * 0.55)
        sy2 = int(self.h * 0.28)
        draw._image.paste(rotated, (sx2, sy2), rotated)

    def _draw_accent_circles(self, draw):
        cx, cy = self.w // 2, self.h // 2
        for rf, _, a in [(0.55, 1, 25), (0.75, 1, 15), (0.90, 1, 10)]:
            draw.ellipse(
                [(cx - int(self.w * rf), cy - int(self.h * rf)),
                 (cx + int(self.w * rf), cy + int(self.h * rf))],
                outline=(255, 255, 255, a), width=1,
            )
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            r = int(self.w * 0.65)
            x1 = cx + int(r * math.cos(rad))
            y1 = cy + int(r * math.sin(rad))
            x2 = cx + int((r + 25) * math.cos(rad))
            y2 = cy + int((r + 25) * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 35), width=1)

    def _draw_warning_triangle(self, draw, cx, cy, size=130):
        h = int(size * math.sqrt(3) / 2)
        pt1 = (cx, cy - h // 2)
        pt2 = (cx - size // 2, cy + h // 2)
        pt3 = (cx + size // 2, cy + h // 2)
        
        # Outline/glow shadow
        draw.polygon([pt1, pt2, pt3], fill=(45, 15, 15, 120), outline=(255, 75, 75, 255), width=6)
        
        # Draw exclamation point
        font_size = int(size * 0.5)
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except:
            font = ImageFont.load_default()
        
        mark = "!"
        mw = draw.textlength(mark, font=font)
        mh = font_size
        draw.text((cx - mw // 2, cy - mh // 2 + 5), mark, fill=(255, 255, 255, 255), font=font)

    def _draw_magnifying_glass(self, draw, cx, cy, size=130):
        r = size // 3
        # Lens circle
        draw.ellipse(
            [(cx - r, cy - r), (cx + r, cy + r)],
            fill=(20, 30, 50, 100),
            outline=(0, 242, 254, 255),
            width=7
        )
        # Lens glare / reflection
        draw.arc(
            [(cx - r + 8, cy - r + 8), (cx + r - 8, cy + r - 8)],
            start=200, end=290,
            fill=(255, 255, 255, 180),
            width=3
        )
        # Handle
        hx1 = cx + int(r * math.cos(math.radians(45)))
        hy1 = cy + int(r * math.sin(math.radians(45)))
        hx2 = cx + int(size * 0.65)
        hy2 = cy + int(size * 0.65)
        draw.line([(hx1, hy1), (hx2, hy2)], fill=(120, 120, 120, 255), width=10)
        draw.line([(hx1, hy1), (hx2, hy2)], fill=(200, 200, 200, 255), width=4)

    def _draw_graphic_decorations(self, draw):
        """Draws premium static graphics (warning triangle on Myth side, magnifying glass on Truth side)."""
        # Warning triangle in top-left (Myth) side
        self._draw_warning_triangle(draw, cx=260, cy=460, size=130)
        # Magnifying glass in bottom-right (Truth) side
        self._draw_magnifying_glass(draw, cx=820, cy=1440, size=130)

    def _draw_light_glare(self, img):
        cx, cy = self.w // 2, self.h // 2
        glare = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glare)
        for rad in range(40, 180, 10):
            alpha = max(0, 25 - (rad - 40) // 7)
            if alpha > 0:
                gd.ellipse(
                    [(cx - rad, cy - rad), (cx + rad, cy + rad)],
                    fill=(255, 255, 255, alpha),
                )
        blurred = glare.filter(ImageFilter.GaussianBlur(radius=15))
        img.paste(blurred, (0, 0), blurred)

    def _draw_sparkles(self, draw):
        for _ in range(6):
            sx = random.randint(int(self.w * 0.08), int(self.w * 0.92))
            sy = random.randint(int(self.h * 0.08), int(self.h * 0.92))
            sz = random.randint(3, 7)
            alpha = random.randint(100, 200)
            c = (255, 255, 255, alpha)
            draw.line([(sx - sz, sy), (sx + sz, sy)], fill=c, width=1)
            draw.line([(sx, sy - sz), (sx, sy + sz)], fill=c, width=1)
            draw.line([(sx - sz // 2, sy - sz // 2), (sx + sz // 2, sy + sz // 2)], fill=c, width=1)
            draw.line([(sx + sz // 2, sy - sz // 2), (sx - sz // 2, sy + sz // 2)], fill=c, width=1)

    def _draw_grid_pattern(self, draw, color=(100, 100, 100), opacity=12):
        spacing = 40
        for x in range(0, self.w, spacing):
            draw.line([(x, 0), (x, self.h)], fill=color + (opacity,), width=1)
        for y in range(0, self.h, spacing):
            draw.line([(0, y), (self.w, y)], fill=color + (opacity,), width=1)

    def _draw_premium_title(self, draw, topic, hook, is_bizarre=False):
        """Draws a premium multi-line title with pixel-based wrapping.
        Automatically shrinks font if text exceeds max width (920px)."""
        accent_color = (0, 200, 255) if is_bizarre else (220, 40, 40)
        max_width = int(self.w * 0.85)  # 920px on 1080w

        topic_text = (topic if topic else "DECLASSIFIED FILE").upper().strip()
        hook_text = (hook if hook else "IS A LIE").upper().strip()

        def _render_wrapped_text(text, font_size, y_start, fill_color, outline_color=(10, 10, 30)):
            font = self._load_font(font_size)
            words = text.split()
            lines = []
            current_line = []
            for word in words:
                test_line = " ".join(current_line + [word])
                line_w = draw.textlength(test_line, font=font)
                if line_w <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))

            # If still too wide, shrink font
            while lines and any(draw.textlength(l, font=font) > max_width for l in lines):
                font_size -= 2
                font = self._load_font(font_size)
                words = text.split()
                lines = []
                current_line = []
                for word in words:
                    test_line = " ".join(current_line + [word])
                    line_w = draw.textlength(test_line, font=font)
                    if line_w <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(" ".join(current_line))

            line_height = font_size + 8
            total_h = len(lines) * line_height
            y = y_start - total_h // 2
            for line in lines:
                lw = draw.textlength(line, font=font)
                x = (self.w - lw) // 2
                outline_w = max(2, font_size // 15)
                for dx in range(-outline_w, outline_w + 1):
                    for dy in range(-outline_w, outline_w + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), line, fill=outline_color + (255,), font=font)
                draw.text((x, y), line, fill=fill_color + (255,), font=font)
                y += line_height
            return y

        # Topic line (white), then hook below (accent)
        base_font_size_top = int(self.w * 0.055)
        base_font_size_bot = int(self.w * 0.065)
        y_top = self.h // 2 - int(self.h * 0.10)

        # Adjust available space: both topic and hook need to fit
        y_bottom = _render_wrapped_text(
            topic_text, base_font_size_top, y_top,
            fill_color=(255, 255, 255)
        ) + 12

        # If hook would go off-screen, scale down
        if y_bottom + base_font_size_bot * 3 > self.h:
            base_font_size_bot = int(base_font_size_bot * 0.8)
        if y_bottom < y_top + 10:
            y_bottom = y_top + int(self.h * 0.03)

        _render_wrapped_text(
            hook_text, base_font_size_bot, y_bottom,
            fill_color=accent_color
        )

    def _draw_bottom_accent_bar(self, draw, is_bizarre=False):
        accent_color = (0, 200, 255) if is_bizarre else (220, 40, 40)
        bar_h = int(self.h * 0.01)
        if bar_h < 4:
            bar_h = 4
        draw.rectangle([0, self.h - bar_h, self.w, self.h], fill=accent_color + (255,))

    def _draw_episode_badge(self, draw, episode_num, is_bizarre=False):
        if episode_num is None:
            return
        badge_str = f"EP. {episode_num:03d}"
        badge_font = self._load_font(int(self.w * 0.03))
        bw = draw.textlength(badge_str, font=badge_font)
        
        bx = self.w - bw - int(self.w * 0.08)
        by = self.h - int(self.h * 0.09)
        
        accent_color = (0, 200, 255) if is_bizarre else (220, 40, 40)
        draw.rounded_rectangle(
            [bx - 12, by - 6, bx + bw + 12, by + int(self.h * 0.04)],
            radius=6,
            fill=(10, 10, 15, 220),
            outline=accent_color,
            width=2
        )
        draw.text((bx, by), badge_str, fill=(255, 255, 255), font=badge_font)

    def generate_from_images(
        self,
        img_myth_path,
        img_truth_path,
        title_text="MYTH vs TRUTH",
        topic_label="",
        episode_num=None,
        use_vignette_blur=True,
    ):
        s = NIGHT_DAY
        base_path = img_myth_path if (img_myth_path and os.path.exists(img_myth_path)) else img_truth_path
        
        if base_path and os.path.exists(base_path):
            raw = Image.open(base_path).convert("RGB")
            filled = self._resize_to_fill(raw, self.w, self.h)
            graded = self._apply_color_grade(
                filled,
                tint=s["myth_tint"],
                tint_strength=s["myth_tint_strength"],
                desaturate=s["myth_desaturate"],
                darken=s["myth_darken"],
            )
            base = graded
        else:
            base = Image.new("RGB", (self.w, self.h), (15, 10, 35))

        base = base.convert("RGBA")
        
        arr = np.array(base)
        noise_mask = np.random.randint(0, 10000, (self.h, self.w)) < 6000
        noise = np.random.randint(-20, 21, (self.h, self.w, 3))
        arr = arr.astype(np.int16)
        arr[noise_mask, :3] = np.clip(arr[noise_mask, :3] + noise[noise_mask], 0, 255)
        arr = arr.astype(np.uint8)
        base = Image.fromarray(arr)

        base = self._draw_vignette(base, strength=0.50)

        overlay = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        self._draw_grid_pattern(od)
        base = Image.alpha_composite(base, overlay)

        circles = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self._draw_accent_circles(ImageDraw.Draw(circles))
        base = Image.alpha_composite(base, circles)

        final_draw = ImageDraw.Draw(base)
        
        self._draw_premium_title(final_draw, topic=topic_label, hook=title_text, is_bizarre=False)
        self._draw_channel_logo(final_draw)
        self._draw_episode_badge(final_draw, episode_num, is_bizarre=False)
        self._draw_bottom_accent_bar(final_draw, is_bizarre=False)
        
        self._draw_light_glare(base)
        self._draw_sparkles(final_draw)
        
        # Paste The Lens mascot (right side, reacting to the topic)
        try:
            from video_engine import VideoEngine
            lens_expr = "shocked" if ("MYTH" in (title_text or "").upper() or "is a lie" in (title_text or "").lower()) else "neutral"
            lens_size = max(80, int(min(self.w, self.h) * 0.11))
            lens_img = VideoEngine._render_static(size=lens_size, expression=lens_expr)
            lens_x = self.w - int(self.w * 0.15) - lens_size // 2
            lens_y = int(self.h * 0.40) - lens_size // 2
            base.paste(lens_img, (lens_x, lens_y), lens_img)
        except Exception as e:
            pass

        return base.convert("RGB")

    def _draw_eeg_waveform(self, draw, cx, y_start, width, height, color=(0, 200, 255), alpha=150):
        """Draw EEG-style brain wave oscilloscope lines."""
        wave_sets = [
            {"amp": 0.4, "freq": 2.0, "offset": 0},
            {"amp": 0.25, "freq": 4.5, "offset": 0.3},
            {"amp": 0.15, "freq": 8.0, "offset": 1.1},
            {"amp": 0.10, "freq": 12.0, "offset": 2.7},
        ]
        step = max(1, width // 120)
        for ws in wave_sets:
            pts = []
            for x_px in range(cx - width // 2, cx + width // 2, step):
                t = (x_px - (cx - width // 2)) / width
                y = y_start + height // 2 + int(
                    height * ws["amp"] * 0.5
                    * (math.sin(2 * math.pi * ws["freq"] * t + ws["offset"])
                       + 0.3 * math.sin(2 * math.pi * ws["freq"] * 3 * t + ws["offset"] * 1.5))
                )
                pts.append((x_px, y))
            if len(pts) > 1:
                c = color + (alpha,)
                for i in range(len(pts) - 1):
                    draw.line([pts[i], pts[i + 1]], fill=c, width=1)
                alpha = max(30, alpha - 30)
                color = (color[0], color[1], max(100, color[2] - 30))

    def _draw_brain_scan_circles(self, draw, cx, cy, max_r, color=(0, 180, 255, 40)):
        """Draw concentric ellipse slices to simulate brain MRI."""
        for r in range(int(max_r * 0.3), int(max_r), int(max_r * 0.08)):
            rx = r
            ry = int(r * 1.15)
            alpha = max(10, 50 - int((r / max_r) * 40))
            draw.ellipse(
                [(cx - rx, cy - ry), (cx + rx, cy + ry)],
                outline=color[:3] + (alpha,),
                width=1,
            )
        midline_y = cy
        for rx_pct in [0.15, 0.30, 0.45]:
            rx = int(max_r * rx_pct)
            draw.line(
                [(cx - rx, midline_y), (cx + rx, midline_y)],
                fill=color[:3] + (25,),
                width=1,
            )

    def generate_bizarre_thumbnail(self, bg_image_path=None, title_text="DECLASSIFIED ANOMALY", topic_label="", episode_num=None):
        if bg_image_path and os.path.exists(bg_image_path):
            try:
                bg_raw = Image.open(bg_image_path).convert("RGB")
                bg_filled = self._resize_to_fill(bg_raw, self.w, self.h)
                bg_arr = np.array(bg_filled, dtype=np.float32)
                dark_arr = bg_arr * 0.35
                tint_arr = np.array([10, 15, 30], dtype=np.float32)
                base_arr = dark_arr * 0.7 + tint_arr * 0.3
                base_arr = np.clip(base_arr, 0, 255).astype(np.uint8)
                base = Image.fromarray(base_arr)
            except Exception:
                base = Image.new("RGB", (self.w, self.h), (10, 15, 30))
        else:
            base = Image.new("RGB", (self.w, self.h), (10, 15, 30))

        base = base.convert("RGBA")
        base = self._draw_vignette(base, strength=0.65)

        grid = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grid)
        self._draw_grid_pattern(gd, color=(0, 180, 255), opacity=8)
        base = Image.alpha_composite(base, grid)

        circles = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self._draw_accent_circles(ImageDraw.Draw(circles))
        base = Image.alpha_composite(base, circles)

        draw = ImageDraw.Draw(base)

        banner_h = int(self.h * 0.055)
        banner_y = int(self.h * 0.03)
        draw.rectangle([0, banner_y, self.w, banner_y + banner_h], fill=(0, 150, 200, 200))
        banner_font = self._load_font(int(self.w * 0.028))
        banner_text = "[ DECLASSIFIED ANOMALY FILE ]"
        bw = draw.textlength(banner_text, font=banner_font)
        draw.text(((self.w - bw) // 2, banner_y + int(banner_h * 0.15)), banner_text, fill=(255, 255, 255), font=banner_font)

        self._draw_premium_title(draw, topic=topic_label, hook=title_text, is_bizarre=True)
        self._draw_channel_logo(draw)
        self._draw_episode_badge(draw, episode_num, is_bizarre=True)
        self._draw_bottom_accent_bar(draw, is_bizarre=True)

        self._draw_light_glare(base)
        self._draw_sparkles(draw)
        
        # Paste The Lens mascot (right side, reacting to the topic)
        try:
            from video_engine import VideoEngine
            lens_expr = "shocked" if ("ANOMALY" in (title_text or "").upper() or "DECLASSIFIED" in (title_text or "").upper()) else "neutral"
            lens_size = max(80, int(min(self.w, self.h) * 0.11))
            lens_img = VideoEngine._render_static(size=lens_size, expression=lens_expr)
            lens_x = self.w - int(self.w * 0.15) - lens_size // 2
            lens_y = int(self.h * 0.40) - lens_size // 2
            base.paste(lens_img, (lens_x, lens_y), lens_img)
        except Exception as e:
            pass

        return base.convert("RGB")

    def save(self, img, output_name, subdir=""):
        save_dir = os.path.join(THUMB_DIR, subdir)
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"{output_name}.png")
        img.save(path, "PNG", optimize=True)
        print(f"[ThumbnailDesigner] Saved: {path}")
        return path


def generate_bizarre_thumbnail(bg_image_path=None, title="DECLASSIFIED ANOMALY", topic="", output_name="bizarre_thumb", episode_num=None):
    short = ThumbnailDesigner(width=1080, height=1920)
    thumb_short = short.generate_bizarre_thumbnail(bg_image_path, title, topic, episode_num=episode_num)
    short.save(thumb_short, output_name, "shorts")
    hd = ThumbnailDesigner(width=1280, height=720)
    thumb_hd = hd.generate_bizarre_thumbnail(bg_image_path, title, topic, episode_num=episode_num)
    hd.save(thumb_hd, f"{output_name}_hd", "youtube")
    print(f"\n[ThumbnailDesigner] Bizarre thumbnails saved to {THUMB_DIR}")
    return os.path.join(THUMB_DIR, "shorts", f"{output_name}.png")


def generate_thumbnail_with_images(
    img_myth_path,
    img_truth_path,
    title="MYTH vs TRUTH",
    output_name="thumb",
    topic="",
    episode_num=None
):
    short = ThumbnailDesigner(width=1080, height=1920)
    thumb_short = short.generate_from_images(img_myth_path, img_truth_path, title, topic_label=topic, episode_num=episode_num)
    short.save(thumb_short, output_name, "shorts")

    hd = ThumbnailDesigner(width=1280, height=720)
    thumb_hd = hd.generate_from_images(img_myth_path, img_truth_path, title, topic_label=topic, episode_num=episode_num)
    hd.save(thumb_hd, f"{output_name}_hd", "youtube")

    print(f"\n[ThumbnailDesigner] Both thumbnails saved to {THUMB_DIR}")
    return os.path.join(THUMB_DIR, "shorts", f"{output_name}.png")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python thumbnail_generator.py <myth_image> <truth_image> [title] [output_name]")
        sys.exit(1)
    myth = sys.argv[1]
    truth = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "MYTH vs TRUTH"
    name = sys.argv[4] if len(sys.argv) > 4 else "daily_audit_thumb"
    generate_thumbnail_with_images(myth, truth, title, name)
