from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps

WIDTH = 1920
HEIGHT = 1080

IMG_DIR = Path("D:/onedrive/dev/caracore-ink-releases/docs/assets/img")
INK_IMG = IMG_DIR / "caracore_ink.png"
DENTAL_IMG = IMG_DIR / "caracore_dental.png"
BEAUTY_IMG = IMG_DIR / "caracore_beauty.png"

OUTPUT_DIR = Path("D:/onedrive/dev/caracore-retro/docs/articles/assets/img")
OUTPUT_FILE = OUTPUT_DIR / "2027_08_12_article_144_01.png"

def fit_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    return ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)

def create_triptych():
    panel_w = WIDTH // 3 # 640
    
    im_ink = fit_crop(Image.open(INK_IMG).convert("RGB"), panel_w, HEIGHT)
    im_dental = fit_crop(Image.open(DENTAL_IMG).convert("RGB"), panel_w, HEIGHT)
    im_beauty = fit_crop(Image.open(BEAUTY_IMG).convert("RGB"), panel_w, HEIGHT)
    
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (13, 17, 23))
    canvas.paste(im_ink, (0, 0))
    canvas.paste(im_dental, (panel_w, 0))
    canvas.paste(im_beauty, (panel_w * 2, 0))
    
    draw = ImageDraw.Draw(canvas, "RGBA")
    
    # Subtle tinted overlays
    # Left: violet
    draw.rectangle([0, 0, panel_w, HEIGHT], fill=(168, 85, 247, 25))
    # Center: turquoise
    draw.rectangle([panel_w, 0, panel_w * 2, HEIGHT], fill=(6, 182, 212, 25))
    # Right: gold
    draw.rectangle([panel_w * 2, 0, WIDTH, HEIGHT], fill=(234, 179, 8, 25))
    
    # Dividers
    draw.line([(panel_w, 0), (panel_w, HEIGHT)], fill=(6, 182, 212, 180), width=3)
    draw.line([(panel_w * 2, 0), (panel_w * 2, HEIGHT)], fill=(234, 179, 8, 180), width=3)
    
    # Bottom and top subtle dark gradients for editorial depth
    for y in range(80):
        alpha = int((1 - y / 80) * 120)
        draw.line([(0, y), (WIDTH, y)], fill=(13, 17, 23, alpha))
    for y in range(HEIGHT - 100, HEIGHT):
        alpha = int(((y - (HEIGHT - 100)) / 100) * 140)
        draw.line([(0, y), (WIDTH, y)], fill=(13, 17, 23, alpha))
        
    canvas.save(OUTPUT_FILE, format="PNG")
    print(f"Generated {OUTPUT_FILE} successfully!")

if __name__ == "__main__":
    create_triptych()

