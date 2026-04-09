#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day2カルーセルサンプル画像生成"""

from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "カルーセル_Day2_サンプル")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Brand colors
GREEN_DARK = (42, 110, 63)
GREEN_MID = (76, 175, 80)
GREEN_LIGHT = (200, 230, 201)
WHITE = (255, 255, 255)
BLACK = (33, 33, 33)
GRAY = (100, 100, 100)

W, H = 1080, 1080

# Try to find a Japanese font
FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
]

FONT_BOLD = None
FONT_REG = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        FONT_BOLD = fp
        break

if not FONT_BOLD:
    print("Warning: No Japanese font found, using default")
    FONT_BOLD = "/System/Library/Fonts/Helvetica.ttc"

FONT_REG = FONT_BOLD

def get_font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    except:
        return ImageFont.load_default()

def draw_rounded_rect(draw, xy, fill, radius=20):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0+radius, y0, x1-radius, y1], fill=fill)
    draw.rectangle([x0, y0+radius, x1, y1-radius], fill=fill)
    draw.pieslice([x0, y0, x0+2*radius, y0+2*radius], 180, 270, fill=fill)
    draw.pieslice([x1-2*radius, y0, x1, y0+2*radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1-2*radius, x0+2*radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1-2*radius, y1-2*radius, x1, y1], 0, 90, fill=fill)

def draw_text_centered(draw, y, text, font, fill=BLACK):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw.text((x, y), text, font=font, fill=fill)

def draw_text_lines(draw, x, y, lines, font, fill=BLACK, line_height=1.5):
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        y += int(h * line_height)
    return y

def add_logo_text(draw):
    """Add small logo text at bottom"""
    font_s = get_font(24)
    text = "🌿 サウンドヒーリング協会  @harmonicscience_jp"
    bbox = draw.textbbox((0, 0), text, font=font_s)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, H - 60), text, font=font_s, fill=GRAY)

def add_slide_number(draw, num, total=5):
    """Add slide indicator dots"""
    dot_y = H - 100
    dot_spacing = 24
    start_x = (W - (total * dot_spacing)) // 2
    for i in range(total):
        x = start_x + i * dot_spacing
        color = GREEN_DARK if i == num else (200, 200, 200)
        draw.ellipse([x, dot_y, x+12, dot_y+12], fill=color)

# ========== Slide 1: Cover (Hook) ==========
img = Image.new('RGB', (W, H), GREEN_DARK)
draw = ImageDraw.Draw(img)

# Gradient effect - lighter at bottom
for y in range(H//2, H):
    alpha = (y - H//2) / (H//2)
    r = int(GREEN_DARK[0] + (GREEN_LIGHT[0] - GREEN_DARK[0]) * alpha * 0.3)
    g = int(GREEN_DARK[1] + (GREEN_LIGHT[1] - GREEN_DARK[1]) * alpha * 0.3)
    b = int(GREEN_DARK[2] + (GREEN_LIGHT[2] - GREEN_DARK[2]) * alpha * 0.3)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

font_xl = get_font(72, bold=True)
font_l = get_font(48, bold=True)
font_m = get_font(36)

draw_text_centered(draw, 200, "「サウンドヒーリング」", font_xl, WHITE)
draw_text_centered(draw, 320, "って聞いて", font_l, WHITE)
draw_text_centered(draw, 400, "どんなイメージですか？", font_l, WHITE)

draw_text_centered(draw, 540, "🤔 なんか怪しい？", font_m, (220, 255, 220))
draw_text_centered(draw, 600, "🤔 スピリチュアル？", font_m, (220, 255, 220))
draw_text_centered(draw, 660, "🤔 科学的根拠あるの？", font_m, (220, 255, 220))

draw_text_centered(draw, 800, "そう思った方にこそ", font_m, WHITE)
draw_text_centered(draw, 860, "読んでほしい5枚です。", font_m, WHITE)

add_slide_number(draw, 0)
img.save(os.path.join(OUTPUT_DIR, "slide1_cover.png"))
print("Slide 1: Cover saved")

# ========== Slide 2: サウンドヒーリングとは ==========
img = Image.new('RGB', (W, H), WHITE)
draw = ImageDraw.Draw(img)

# Green header bar
draw.rectangle([0, 0, W, 120], fill=GREEN_DARK)
draw_text_centered(draw, 30, "サウンドヒーリングとは", get_font(48, bold=True), WHITE)

font_body = get_font(38)
font_body_s = get_font(32)

lines = [
    "サウンドヒーリングとは",
    "「音」を使って",
    "心と体のバランスを整えること。",
    "",
    "特別なことではなく",
    "川のせせらぎを聴いて",
    "ホッとした経験、ありませんか？",
    "",
    "あの感覚を",
    "より意図的に、より深く──",
    "それがサウンドヒーリングです。",
]
draw_text_lines(draw, 80, 180, lines, font_body, BLACK, 1.4)

add_slide_number(draw, 1)
add_logo_text(draw)
img.save(os.path.join(OUTPUT_DIR, "slide2_what.png"))
print("Slide 2: What is SH saved")

# ========== Slide 3: 25年の歴史と実績 ==========
img = Image.new('RGB', (W, H), WHITE)
draw = ImageDraw.Draw(img)

draw.rectangle([0, 0, W, 120], fill=GREEN_DARK)
draw_text_centered(draw, 30, "25年の歴史と実績", get_font(48, bold=True), WHITE)

lines = [
    "私たちの活動は",
    "「気持ちいい」だけでは終わりません。",
]
draw_text_lines(draw, 80, 180, lines, font_body, BLACK, 1.4)

# Academic list with icons
y = 340
items = [
    "📚 日本温泉気候物理医学会",
    "📚 日本抗加齢医学会",
    "📚 国際生命情報科学会（ISLIS）",
]
for item in items:
    draw.text((80, y), item, font=get_font(34), fill=BLACK)
    y += 60

lines2 = [
    "",
    "など複数の学会で",
    "体験出展、研究発表を行っています。",
    "",
    "設立から25年。",
    "音の可能性を",
    "真剣に探求し続けています。",
]
y = draw_text_lines(draw, 80, y, lines2, font_body_s, BLACK, 1.4)

# Try to overlay the conference photo
PHOTO_PATH = os.path.join(os.path.dirname(__file__), "カルーセル画像素材/Day2_Day4/Day2 ③第78回日本温泉気候物理医学会.png")
if os.path.exists(PHOTO_PATH):
    photo = Image.open(PHOTO_PATH)
    photo = photo.resize((300, 200))
    img.paste(photo, (700, 350))
    # Add border
    draw = ImageDraw.Draw(img)
    draw.rectangle([698, 348, 1002, 552], outline=GREEN_MID, width=3)

add_slide_number(draw, 2)
add_logo_text(draw)
img.save(os.path.join(OUTPUT_DIR, "slide3_history.png"))
print("Slide 3: History saved")

# ========== Slide 4: 企業・医療機関にも ==========
img = Image.new('RGB', (W, H), WHITE)
draw = ImageDraw.Draw(img)

draw.rectangle([0, 0, W, 120], fill=GREEN_DARK)
draw_text_centered(draw, 30, "企業・医療機関にも", get_font(48, bold=True), WHITE)

y = 180
items = [
    ("🏢", "企業の健康プログラムに導入"),
    ("🏥", "整形外科で毎月の体験会を開催"),
    ("🚢", "米国Well-Beingクルーズで講演・体験"),
]
for emoji, text in items:
    draw.text((80, y), emoji, font=get_font(40), fill=BLACK)
    draw.text((140, y + 5), text, font=get_font(34), fill=BLACK)
    y += 80

y += 30
lines = [
    "「本当に良いものなら",
    "企業や医療機関が採用するはず」",
    "",
    "その通りです。",
    "だから私たちは実績で示します。",
]
draw_text_lines(draw, 80, y, lines, font_body_s, BLACK, 1.5)

# Try to add cruise photo
CRUISE_PATH = os.path.join(os.path.dirname(__file__), "カルーセル画像素材/Day2_Day4/Day2 ④Well-Being  CruiseでのSH体験 2019 _0145.JPG")
if os.path.exists(CRUISE_PATH):
    photo = Image.open(CRUISE_PATH)
    photo.thumbnail((400, 250))
    pw, ph = photo.size
    img.paste(photo, ((W - pw) // 2, 700))
    draw = ImageDraw.Draw(img)

add_slide_number(draw, 3)
add_logo_text(draw)
img.save(os.path.join(OUTPUT_DIR, "slide4_corporate.png"))
print("Slide 4: Corporate saved")

# ========== Slide 5: CTA ==========
img = Image.new('RGB', (W, H), GREEN_DARK)
draw = ImageDraw.Draw(img)

# Gradient
for y in range(H):
    alpha = y / H
    r = int(GREEN_DARK[0] + (42 - GREEN_DARK[0]) * alpha * 0.5)
    g = int(GREEN_DARK[1] + (80 - GREEN_DARK[1]) * alpha * 0.5)
    b = int(GREEN_DARK[2] + (42 - GREEN_DARK[2]) * alpha * 0.5)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

font_cta = get_font(42, bold=True)
font_cta_s = get_font(36)

lines = [
    "「怪しい」と思っていたものが",
    "「ちょっと気になる」に",
    "変わったら嬉しいです。",
]
draw_text_lines(draw, 80, 200, lines, font_cta, WHITE, 1.6)

draw_text_centered(draw, 430, "まずは体験してみませんか？", font_cta, (220, 255, 220))

# CTA buttons
draw_rounded_rect(draw, (200, 540, 880, 620), WHITE, 40)
draw_text_centered(draw, 555, "🆓 毎月の無料体験会", get_font(36, bold=True), GREEN_DARK)

draw_rounded_rect(draw, (200, 660, 880, 740), WHITE, 40)
draw_text_centered(draw, 675, "💻 オンラインでも参加OK", get_font(36, bold=True), GREEN_DARK)

draw.text((80, 820), "━━━━━━━━━━━━━━━━━━━━━", font=get_font(24), fill=(150, 200, 150))
draw_text_centered(draw, 870, "▼ 詳しくはプロフィールから", font_cta_s, WHITE)

add_slide_number(draw, 4)
img.save(os.path.join(OUTPUT_DIR, "slide5_cta.png"))
print("Slide 5: CTA saved")

print(f"\nAll slides saved to: {OUTPUT_DIR}")
