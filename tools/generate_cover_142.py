"""Gera a imagem de capa editorial para o Artigo 142 do blog retro."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1600
HEIGHT = 900
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "articles" / "assets" / "img"
OUTPUT_FILE = OUTPUT_DIR / "2027_07_28_article_142_01.png"
FONT_DIR = Path("C:/Windows/Fonts")

def get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [FONT_DIR / name, FONT_DIR / "segoeui.ttf", FONT_DIR / "arial.ttf"]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size)
            except Exception:
                pass
    return ImageFont.load_default()

FONT_TITLE = get_font("segoeuib.ttf", 54)
FONT_SUBTITLE = get_font("segoeui.ttf", 24)
FONT_SECTION = get_font("segoeuib.ttf", 20)
FONT_MONO = get_font("consola.ttf", 16)
FONT_BADGE = get_font("segoeuib.ttf", 15)
FONT_LABEL = get_font("segoeuib.ttf", 14)

def blend(c1, c2, ratio):
    return tuple(int(a + (b - a) * ratio) for a, b in zip(c1, c2))

def create_cover():
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    
    # Gradient background: deep night navy to slate cyan
    c_top_left = (6, 16, 32)
    c_bot_left = (10, 28, 52)
    c_top_right = (12, 22, 42)
    c_bot_right = (16, 44, 76)
    
    for y in range(HEIGHT):
        v = y / HEIGHT
        left_col = blend(c_top_left, c_bot_left, v)
        right_col = blend(c_top_right, c_bot_right, v)
        for x in range(WIDTH):
            h = x / WIDTH
            pixels[x, y] = blend(left_col, right_col, h)
            
    draw = ImageDraw.Draw(image, "RGBA")
    
    # Subtle tech grid in the background
    for x in range(0, WIDTH, 60):
        alpha = 35 if x % 180 == 0 else 18
        draw.line((x, 140, x, HEIGHT), fill=(60, 140, 200, alpha), width=1)
    for y in range(140, HEIGHT, 50):
        alpha = 35 if y % 150 == 0 else 18
        draw.line((0, y, WIDTH, y), fill=(60, 140, 200, alpha), width=1)
        
    # Top banner bar
    draw.rectangle((0, 0, WIDTH, 120), fill=(4, 10, 22, 230))
    draw.line((0, 120, WIDTH, 120), fill=(84, 215, 232, 100), width=2)
    
    # Brand and edition badge
    draw.rounded_rectangle((60, 32, 280, 68), radius=6, fill=(18, 48, 80, 200), outline=(84, 215, 232, 180), width=1)
    draw.text((75, 42), "CARA CORE RETRO", font=FONT_BADGE, fill=(126, 232, 240, 255))
    draw.text((305, 43), "CADERNO DIGITAL // ENGENHARIA & IA // JULHO 2027", font=FONT_BADGE, fill=(160, 180, 205, 240))
    
    # Article headline on cover
    draw.text((60, 145), "A Ilusao da Velocidade", font=FONT_TITLE, fill=(245, 248, 252, 255))
    draw.text((60, 215), "DeepSeek Flash v4, 2.500 testes e a engenharia de chao de fabrica do CaraCore Hub", font=FONT_SUBTITLE, fill=(255, 184, 107, 255))
    
    # 3 Main Panels comparing Synthetic Speed vs Real Engineering Gateways
    
    # Panel 1: DeepSeek Flash v4 (Speed / Generation)
    box1 = (60, 280, 480, 720)
    draw.rounded_rectangle(box1, radius=16, fill=(8, 24, 46, 230), outline=(84, 215, 232, 200), width=2)
    draw.rounded_rectangle((80, 305, 460, 345), radius=8, fill=(16, 52, 88, 240))
    draw.text((95, 315), "1. DEEPSEEK FLASH V4", font=FONT_SECTION, fill=(84, 215, 232, 255))
    
    items1 = [
        ("Velocidade Flash", "Centenas de tokens/s via NIM"),
        ("Sintese de Codigo", "Metodos, controllers e specs"),
        ("Armadilha", "Gera o plausivel, nao o provado"),
        ("Risco Detectado", "Auditoria mockada sem tabela real"),
        ("Falso Positivo", "Testes que confirmam a propria suposicao"),
        ("Sessao Java", "Esquece Serializable (SpotBugs barra)"),
    ]
    y_pos = 370
    for label, desc in items1:
        draw.text((85, y_pos), f"> {label}:", font=FONT_LABEL, fill=(255, 184, 107, 255))
        draw.text((85, y_pos + 18), desc, font=FONT_MONO, fill=(200, 215, 230, 220))
        y_pos += 52

    # Panel 2: Gates de Verificacao (O Filtro Rigoroso)
    box2 = (520, 280, 1040, 720)
    draw.rounded_rectangle(box2, radius=16, fill=(10, 28, 54, 240), outline=(255, 184, 107, 220), width=2)
    draw.rounded_rectangle((540, 305, 1020, 345), radius=8, fill=(36, 48, 40, 240), outline=(126, 232, 181, 150))
    draw.text((555, 315), "2. PIPELINE DE GATES (E1 - E6)", font=FONT_SECTION, fill=(126, 232, 181, 255))
    
    gates = [
        ("E1: 2.555 Testes", "Surefire limpo (core/api/web/pers)"),
        ("E2: SQLite Real", "Concorrencia fisica, sem SQLITE_BUSY"),
        ("E3: JSPC Precompile", "78 JSPs + validacao estrita de EL"),
        ("E4: Sondas HTTP", "21 rotas anom. 401, RBAC Admin 200"),
        ("E5: Playwright E2E", "Electron 35 + Tomcat 10.1 empacotados"),
        ("E6: SpotBugs + OWASP", "Zero alta/media, 1 CVE triado"),
    ]
    y_pos = 370
    for label, desc in gates:
        draw.rounded_rectangle((540, y_pos, 1020, y_pos + 44), radius=6, fill=(16, 38, 66, 200), outline=(84, 160, 210, 80), width=1)
        draw.text((555, y_pos + 5), f"[PASS] {label}", font=FONT_LABEL, fill=(126, 232, 181, 255))
        draw.text((555, y_pos + 23), desc, font=FONT_MONO, fill=(185, 205, 225, 240))
        y_pos += 52

    # Panel 3: CaraCore Hub 2.1 (O Chão Firme)
    box3 = (1080, 280, 1540, 720)
    draw.rounded_rectangle(box3, radius=16, fill=(8, 24, 46, 230), outline=(126, 232, 181, 200), width=2)
    draw.rounded_rectangle((1100, 305, 1520, 345), radius=8, fill=(16, 52, 88, 240))
    draw.text((1115, 315), "3. CARACORE HUB 2.1", font=FONT_SECTION, fill=(126, 232, 181, 255))
    
    items3 = [
        ("Stack Local", "Java 25 + Tomcat 10.1 + Electron 35"),
        ("Soberania", "SQLite WAL local no PC do lojista"),
        ("Contrato 403", "JSON padronizado (ContratoDeErro)"),
        ("Auditoria Real", "V18 usuario_auditoria persistida"),
        ("Honestidade", "Pre-release identificada, GA em 2027"),
        ("Decisao Humana", "O engenheiro define o rumo e o freio"),
    ]
    y_pos = 370
    for label, desc in items3:
        draw.text((1105, y_pos), f"* {label}:", font=FONT_LABEL, fill=(84, 215, 232, 255))
        draw.text((1105, y_pos + 18), desc, font=FONT_MONO, fill=(200, 215, 230, 220))
        y_pos += 52

    # Bottom status bar
    draw.rectangle((0, 780, WIDTH, HEIGHT), fill=(4, 12, 26, 255))
    draw.line((0, 780, WIDTH, 780), fill=(255, 184, 107, 180), width=2)
    
    metrics = [
        ("VERIFY EXECUTION", "17m 26s PASS"),
        ("TOTAL TESTES", "2.555 PASS / 0 FAIL"),
        ("ARVORE GIT", "dirtyEntries: 0"),
        ("PROMOTABLE STATUS", "TRUE (rc1.6)"),
        ("GA TARGET", "06/04/2027"),
    ]
    x_metric = 60
    for title, val in metrics:
        draw.text((x_metric, 805), title, font=FONT_BADGE, fill=(140, 165, 195, 240))
        draw.text((x_metric, 835), val, font=FONT_SECTION, fill=(245, 248, 252, 255))
        x_metric += 300

    image.save(OUTPUT_FILE, format="PNG")
    print(f"Imagem criada: {OUTPUT_FILE} ({WIDTH}x{HEIGHT})")

if __name__ == "__main__":
    create_cover()
