#!/usr/bin/env python3
"""
Instagram投稿用画像3枚を生成（月・火・水）
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

BASE = os.path.dirname(__file__)
OUT = os.path.join(BASE, 'instagram_drafts')
os.makedirs(OUT, exist_ok=True)

SIZE = (1080, 1080)

# Fonts
FONT_BOLD = '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc'
FONT_LIGHT = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
FONT_ROUND = '/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc'
FONT_MINCHO = '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc'

# Colors
GREEN_DARK = (46, 125, 50)
GREEN_MED = (76, 175, 80)
GREEN_LIGHT = (200, 230, 201)
GREEN_BG = (232, 245, 233)
BLUE_DARK = (21, 101, 192)
BLUE_LIGHT = (227, 242, 253)
ORANGE = (230, 81, 0)
ORANGE_LIGHT = (255, 243, 224)
WHITE = (255, 255, 255)
DARK = (33, 33, 33)
GRAY = (117, 117, 117)
CREAM = (250, 248, 240)


def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    """Draw a rounded rectangle"""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def create_post1_science():
    """月曜: IG-C-001 自律神経と自然音の関係（カルーセル1枚目表紙）"""
    img = Image.new('RGB', SIZE, GREEN_BG)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([0, 0, 1080, 8], fill=GREEN_DARK)

    # "保存推奨" badge
    font_badge = ImageFont.truetype(FONT_BOLD, 28)
    badge_text = "保存推奨"
    draw.rounded_rectangle([60, 50, 260, 100], radius=25, fill=GREEN_DARK)
    draw.text((95, 55), badge_text, font=font_badge, fill=WHITE)

    # Source reference (top right)
    font_source = ImageFont.truetype(FONT_LIGHT, 18)
    draw.text((700, 65), "出典: 日本温泉気候医学会 2013", font=font_source, fill=GRAY)

    # Main title area
    font_main = ImageFont.truetype(FONT_BOLD, 52)
    font_sub = ImageFont.truetype(FONT_LIGHT, 36)

    draw.text((80, 160), "自律神経が", font=font_main, fill=DARK)
    draw.text((80, 225), "乱れやすい人へ", font=font_main, fill=DARK)

    # Accent line
    draw.rectangle([80, 300, 400, 306], fill=GREEN_MED)

    # Sub heading
    font_highlight = ImageFont.truetype(FONT_BOLD, 44)
    draw.text((80, 340), "自然音で整う", font=font_highlight, fill=GREEN_DARK)
    draw.text((80, 400), "科学的メカニズム", font=font_highlight, fill=GREEN_DARK)

    # Data box
    draw.rounded_rectangle([60, 490, 1020, 750], radius=20, fill=WHITE)
    draw.rounded_rectangle([60, 490, 1020, 545], radius=20, fill=GREEN_DARK)
    draw.rectangle([60, 525, 1020, 545], fill=GREEN_DARK)

    font_box_title = ImageFont.truetype(FONT_BOLD, 26)
    draw.text((90, 498), "学会発表データ（成人女性10名対象）", font=font_box_title, fill=WHITE)

    font_data = ImageFont.truetype(FONT_BOLD, 34)
    font_data_desc = ImageFont.truetype(FONT_LIGHT, 26)

    # Data points with checkmarks
    y = 570
    items = [
        ("9名で心拍数が低下", GREEN_DARK),
        ("副交感神経の機能が向上", GREEN_DARK),
        ("リラックス反応を確認", GREEN_DARK),
    ]
    for text, color in items:
        draw.text((110, y), "✓", font=font_data, fill=color)
        draw.text((160, y + 3), text, font=font_data_desc, fill=DARK)
        y += 55

    # Bottom section - key insight
    draw.rounded_rectangle([60, 790, 1020, 920], radius=20, fill=(255, 255, 240))
    draw.rounded_rectangle([60, 790, 1020, 920], radius=20, outline=ORANGE, width=2)

    font_insight = ImageFont.truetype(FONT_ROUND, 28)
    draw.text((100, 810), "人体の約70%は水分", font=ImageFont.truetype(FONT_BOLD, 32), fill=ORANGE)
    draw.text((100, 860), "音は水中を空気の4倍以上の速さで伝わります", font=font_insight, fill=DARK)

    # Footer
    font_footer = ImageFont.truetype(FONT_LIGHT, 22)
    draw.text((80, 960), "NPO法人サウンドヒーリング協会", font=font_footer, fill=GRAY)
    draw.text((80, 990), "@sound_healing_association", font=font_footer, fill=GREEN_DARK)

    # Bottom accent bar
    draw.rectangle([0, 1072, 1080, 1080], fill=GREEN_DARK)

    img.save(os.path.join(OUT, '01_月_自律神経と自然音.png'), quality=95)
    print("Created: 01_月_自律神経と自然音.png")


def create_post2_event():
    """火曜: イベント告知「ここちよい音の日」"""
    img = Image.new('RGB', SIZE, ORANGE_LIGHT)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([0, 0, 1080, 8], fill=ORANGE)

    # Event badge
    font_badge = ImageFont.truetype(FONT_BOLD, 28)
    draw.rounded_rectangle([60, 50, 300, 100], radius=25, fill=ORANGE)
    draw.text((85, 55), "イベント告知", font=font_badge, fill=WHITE)

    # "毎月開催" sub badge
    font_sub_badge = ImageFont.truetype(FONT_BOLD, 22)
    draw.rounded_rectangle([320, 55, 460, 95], radius=18, fill=WHITE, outline=ORANGE, width=2)
    draw.text((340, 60), "毎月開催", font=font_sub_badge, fill=ORANGE)

    # Main title
    font_event_title = ImageFont.truetype(FONT_BOLD, 60)
    draw.text((80, 150), "ここちよい", font=font_event_title, fill=DARK)
    draw.text((80, 225), "音の日", font=font_event_title, fill=DARK)

    # Accent
    draw.rectangle([80, 310, 350, 316], fill=ORANGE)

    # Description
    font_desc = ImageFont.truetype(FONT_ROUND, 30)
    draw.text((80, 345), "自然音とヒーリングの無料体験会", font=font_desc, fill=GRAY)

    # Info box
    draw.rounded_rectangle([60, 420, 1020, 850], radius=20, fill=WHITE)

    font_label = ImageFont.truetype(FONT_BOLD, 26)
    font_value = ImageFont.truetype(FONT_LIGHT, 28)

    items = [
        ("日時", "毎月第3土曜日 13:00〜15:00"),
        ("場所", "オンライン（Zoom）"),
        ("参加費", "無料"),
        ("対象", "どなたでも参加OK（初めての方歓迎）"),
    ]
    y = 450
    for label, value in items:
        draw.rounded_rectangle([90, y, 230, y + 40], radius=8, fill=ORANGE)
        draw.text((105, y + 4), label, font=font_label, fill=WHITE)
        draw.text((250, y + 4), value, font=font_value, fill=DARK)
        y += 70

    # What you'll experience
    draw.rectangle([90, y + 10, 1000, y + 12], fill=(230, 230, 230))
    y += 30

    font_what = ImageFont.truetype(FONT_BOLD, 24)
    draw.text((90, y), "体験できること", font=font_what, fill=ORANGE)
    y += 45

    font_item = ImageFont.truetype(FONT_ROUND, 24)
    exp_items = [
        "自然音の試聴体験",
        "呼吸法ワークショップ",
        "セラピストによるQ&A",
    ]
    for item in exp_items:
        draw.text((110, y), f"● {item}", font=font_item, fill=DARK)
        y += 40

    # CTA box
    draw.rounded_rectangle([60, 880, 1020, 1000], radius=20, fill=ORANGE)
    font_cta = ImageFont.truetype(FONT_BOLD, 34)
    font_cta_sub = ImageFont.truetype(FONT_LIGHT, 24)
    draw.text((180, 895), "参加申込はプロフィールから", font=font_cta, fill=WHITE)
    draw.text((240, 945), "お気軽にDMでもお問い合わせください", font=font_cta_sub, fill=(255, 230, 200))

    # Footer
    font_footer = ImageFont.truetype(FONT_LIGHT, 22)
    draw.text((80, 1020), "NPO法人サウンドヒーリング協会", font=font_footer, fill=GRAY)
    draw.text((80, 1048), "@sound_healing_association", font=font_footer, fill=ORANGE)

    # Bottom accent bar
    draw.rectangle([0, 1072, 1080, 1080], fill=ORANGE)

    img.save(os.path.join(OUT, '02_火_ここちよい音の日.png'), quality=95)
    print("Created: 02_火_ここちよい音の日.png")


def create_post3_quote():
    """水曜: IG-S-001 名言「音は心の糧である」"""
    img = Image.new('RGB', SIZE, CREAM)
    draw = ImageDraw.Draw(img)

    # Decorative top/bottom borders
    for i in range(0, 1080, 40):
        alpha = 80 + (i % 80)
        color = (46, 125, 50, alpha)
    draw.rectangle([0, 0, 1080, 4], fill=GREEN_DARK)
    draw.rectangle([0, 1076, 1080, 1080], fill=GREEN_DARK)

    # Decorative frame
    draw.rounded_rectangle([40, 40, 1040, 1040], radius=30, outline=GREEN_LIGHT, width=3)
    draw.rounded_rectangle([60, 60, 1020, 1020], radius=25, outline=GREEN_MED, width=1)

    # Quote category badge
    font_badge = ImageFont.truetype(FONT_BOLD, 24)
    draw.rounded_rectangle([80, 80, 260, 120], radius=15, fill=GREEN_DARK)
    draw.text((108, 84), "名言・理念", font=font_badge, fill=WHITE)

    # Large quote mark
    font_quote = ImageFont.truetype(FONT_MINCHO, 120)
    draw.text((100, 160), "「", font=font_quote, fill=GREEN_LIGHT)

    # Main quote text
    font_main_quote = ImageFont.truetype(FONT_MINCHO, 64)
    # Center the quote
    quote_lines = ["音は", "心の糧で", "ある"]
    y = 280
    for line in quote_lines:
        bbox = draw.textbbox((0, 0), line, font=font_main_quote)
        w = bbox[2] - bbox[0]
        x = (1080 - w) // 2
        draw.text((x, y), line, font=font_main_quote, fill=DARK)
        y += 90

    # Closing quote mark
    draw.text((800, y - 60), "」", font=font_quote, fill=GREEN_LIGHT)

    # Attribution line
    draw.rectangle([400, y + 30, 680, y + 33], fill=GREEN_MED)

    font_attr = ImageFont.truetype(FONT_BOLD, 30)
    attr_text = "喜田圭一郎"
    bbox = draw.textbbox((0, 0), attr_text, font=font_attr)
    w = bbox[2] - bbox[0]
    draw.text(((1080 - w) // 2, y + 55), attr_text, font=font_attr, fill=GREEN_DARK)

    font_attr_sub = ImageFont.truetype(FONT_LIGHT, 22)
    sub_text = "サウンドヒーリング協会 理事長"
    bbox = draw.textbbox((0, 0), sub_text, font=font_attr_sub)
    w = bbox[2] - bbox[0]
    draw.text(((1080 - w) // 2, y + 100), sub_text, font=font_attr_sub, fill=GRAY)

    # Philosophy box
    draw.rounded_rectangle([100, 740, 980, 920], radius=15, fill=GREEN_BG)

    font_phil = ImageFont.truetype(FONT_ROUND, 24)
    phil_lines = [
        "私たちの体は、耳だけでなく",
        "全身で音を聴いています。",
        "",
        "自然の音は、心と体に",
        "本来のリズムを取り戻してくれます。",
    ]
    py = 760
    for line in phil_lines:
        if line == "":
            py += 10
            continue
        bbox = draw.textbbox((0, 0), line, font=font_phil)
        w = bbox[2] - bbox[0]
        draw.text(((1080 - w) // 2, py), line, font=font_phil, fill=DARK)
        py += 36

    # Footer
    font_footer = ImageFont.truetype(FONT_LIGHT, 22)
    draw.text((80, 960), "NPO法人サウンドヒーリング協会", font=font_footer, fill=GRAY)
    draw.text((80, 988), "@sound_healing_association", font=font_footer, fill=GREEN_DARK)

    img.save(os.path.join(OUT, '03_水_音は心の糧.png'), quality=95)
    print("Created: 03_水_音は心の糧.png")


if __name__ == '__main__':
    create_post1_science()
    create_post2_event()
    create_post3_quote()

    # Write captions
    captions = {
        '01_月_caption.txt': """【自律神経が整う「音」の力】

最近こんな不調、ありませんか？

・寝つきが悪い
・朝起きるのがつらい
・なんとなくダルい

それ、自律神経の乱れかもしれません。

━━━━━━━━━━━━

2013年の学会発表では、
成人女性10名への実験で
9名に副交感神経の機能向上を確認。

心拍数が低下し、
体がリラックスモードに
切り替わったのです。

━━━━━━━━━━━━

なぜ自然音は体に届くの？

人体の約70%は水分。
音は水中を空気の4倍以上の速さで伝わります。

だから、
自然音は体の奥深くまで響き、
内側からリラックスを促すんです。

━━━━━━━━━━━━

今日から試せる3つの習慣

1. 朝：鳥のさえずりで目覚める
2. 昼：小川の音で5分休憩
3. 夜：波の音で眠りにつく

━━━━━━━━━━━━

体本来の力を取り戻す。
それがサウンドヒーリングです。

オンラインセミナーでは
実践的なセルフケア法をお伝えしています。
詳しくはプロフィールのリンクから。

#自然音 #自律神経 #自律神経を整える
#サウンドヒーリング #リラックス #睡眠改善
#ストレス解消 #ヒーリング #癒し
#副交感神経 #セルフケア #ウェルビーイング""",

        '02_火_caption.txt': """【毎月開催】ここちよい音の日

自然音とヒーリングの無料体験会、
毎月開催しています。

━━━━━━━━━━━━

日時：毎月第3土曜日 13:00〜15:00
場所：オンライン（Zoom）
参加費：無料
対象：どなたでもOK（初めての方歓迎）

━━━━━━━━━━━━

体験できること

● 自然音の試聴体験
● 呼吸法ワークショップ
● セラピストによるQ&A

━━━━━━━━━━━━

「サウンドヒーリングって何？」
「自然音ってどんな効果があるの？」

そんな疑問にお答えします。

まずは体験してみてください。
きっと、体が教えてくれます。

━━━━━━━━━━━━

参加申込はプロフィールのリンクから。
お気軽にDMでもお問い合わせください。

#ここちよい音の日 #サウンドヒーリング
#無料体験 #オンラインイベント #自然音
#ヒーリング体験 #リラックス #癒しの時間
#呼吸法 #ウェルビーイング #セルフケア
#音の力 #心と体を整える""",

        '03_水_caption.txt': """「音は心の糧である」
── 喜田圭一郎（サウンドヒーリング協会 理事長）

━━━━━━━━━━━━

私たちの体は、
耳だけでなく全身で音を聴いています。

自然の音は、
心と体に本来のリズムを取り戻してくれます。

━━━━━━━━━━━━

忙しい毎日の中で、
ふと立ち止まって
自然の音に耳を傾けてみてください。

鳥のさえずり、
川のせせらぎ、
波の音...

それだけで、
心がすこし軽くなるはずです。

━━━━━━━━━━━━

サウンドヒーリング協会は
2001年の設立以来、
「心と体に自然のリズムを取り戻す」
をコンセプトに活動しています。

オンラインセミナーで
実践的なセルフケア法をお伝えしています。
詳しくはプロフィールのリンクから。

#音は心の糧 #サウンドヒーリング #自然音
#心と体を整える #名言 #ウェルビーイング
#セルフケア #リラックス #癒し #ヒーリング
#自律神経 #マインドフルネス #呼吸法"""
    }

    for fname, text in captions.items():
        with open(os.path.join(OUT, fname), 'w') as f:
            f.write(text.strip())
        print(f"Created: {fname}")

    print(f"\nAll files saved to: {OUT}")
