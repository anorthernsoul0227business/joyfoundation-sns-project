#!/usr/bin/env python3
"""
X（Twitter）投稿90本 PDF生成
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, Flowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import os
import re

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))

FONT_GOTHIC = 'HeiseiKakuGo-W5'
FONT_MINCHO = 'HeiseiMin-W3'

PRIMARY = HexColor('#2E7D32')
SECONDARY = HexColor('#1565C0')
ACCENT = HexColor('#E65100')
DARK = HexColor('#212121')
GRAY = HexColor('#616161')
LIGHT_GRAY = HexColor('#F5F5F5')
WHITE = HexColor('#FFFFFF')
X_BLUE = HexColor('#1DA1F2')
LIGHT_BLUE = HexColor('#E8F4FD')
LIGHT_GREEN = HexColor('#E8F5E9')
LIGHT_ORANGE = HexColor('#FFF3E0')
LIGHT_PURPLE = HexColor('#F3E5F5')

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'X投稿90本.pdf')
SOURCE_PATH = os.path.join(os.path.dirname(__file__), 'コンテンツ', 'X投稿90本.md')


class RoundedBox(Flowable):
    """Rounded rectangle box with content"""
    def __init__(self, width, content_lines, bg_color=LIGHT_BLUE, code='', category=''):
        Flowable.__init__(self)
        self.width = width
        self.content_lines = content_lines
        self.bg_color = bg_color
        self.code = code
        self.category = category
        # Calculate height
        self.line_height = 12
        self.padding = 8
        self.header_height = 18
        self.height = self.header_height + self.padding * 2 + len(content_lines) * self.line_height + 4

    def draw(self):
        canvas = self.canv
        # Background
        canvas.setFillColor(self.bg_color)
        canvas.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=0)
        # Header bar
        canvas.setFillColor(X_BLUE)
        canvas.roundRect(0, self.height - self.header_height, self.width, self.header_height, 6, fill=1, stroke=0)
        canvas.setFillColor(X_BLUE)
        canvas.rect(0, self.height - self.header_height, self.width, 8, fill=1, stroke=0)
        # Header text
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_GOTHIC, 9)
        canvas.drawString(10, self.height - 13, f'{self.code}')
        canvas.drawRightString(self.width - 10, self.height - 13, self.category)
        # Content
        canvas.setFillColor(DARK)
        canvas.setFont(FONT_MINCHO, 9)
        y = self.height - self.header_height - self.padding - 10
        for line in self.content_lines:
            if line.startswith('#'):
                canvas.setFillColor(X_BLUE)
                canvas.setFont(FONT_MINCHO, 8)
            canvas.drawString(self.padding + 4, y, line)
            if line.startswith('#'):
                canvas.setFillColor(DARK)
                canvas.setFont(FONT_MINCHO, 9)
            y -= self.line_height


def parse_posts(filepath):
    """Parse markdown file to extract posts"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    posts = []
    current_category = ''
    current_subcategory = ''

    # Split by post markers
    sections = content.split('**X-')

    for section in sections[1:]:  # skip first (header)
        # Extract code
        code_match = re.match(r'(\d+)\*\*', section)
        if not code_match:
            continue
        code = f'X-{code_match.group(1)}'

        # Extract content between ``` markers
        content_match = re.search(r'```\n(.*?)\n```', section, re.DOTALL)
        if not content_match:
            continue
        post_content = content_match.group(1).strip()

        # Determine category from code number
        num = int(code_match.group(1))
        if num <= 12:
            category = '科学データ・Tips'
            subcategory = '自律神経系'
        elif num <= 24:
            category = '科学データ・Tips'
            subcategory = '自然音・1/fゆらぎ系'
        elif num <= 36:
            category = '科学データ・Tips'
            subcategory = '自己回復力系'
        elif num <= 54:
            category = '名言・理念'
            subcategory = ''
        elif num <= 72:
            category = 'イベント告知'
            subcategory = ''
        else:
            category = '記事シェア用'
            subcategory = ''

        posts.append({
            'code': code,
            'content': post_content,
            'category': category,
            'subcategory': subcategory,
        })

    return posts


def build_pdf():
    posts = parse_posts(SOURCE_PATH)

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle('JTitle', fontName=FONT_GOTHIC, fontSize=22, leading=30,
                             textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=5*mm)
    s_subtitle = ParagraphStyle('JSubtitle', fontName=FONT_GOTHIC, fontSize=12, leading=16,
                                textColor=GRAY, alignment=TA_CENTER, spaceAfter=8*mm)
    s_h1 = ParagraphStyle('JH1', fontName=FONT_GOTHIC, fontSize=16, leading=22,
                          textColor=PRIMARY, spaceBefore=6*mm, spaceAfter=4*mm)
    s_h2 = ParagraphStyle('JH2', fontName=FONT_GOTHIC, fontSize=13, leading=18,
                          textColor=SECONDARY, spaceBefore=5*mm, spaceAfter=3*mm)
    s_h3 = ParagraphStyle('JH3', fontName=FONT_GOTHIC, fontSize=11, leading=15,
                          textColor=DARK, spaceBefore=3*mm, spaceAfter=2*mm)
    s_body = ParagraphStyle('JBody', fontName=FONT_MINCHO, fontSize=9.5, leading=15,
                            textColor=DARK, spaceAfter=2*mm)
    s_caption = ParagraphStyle('JCaption', fontName=FONT_GOTHIC, fontSize=8, leading=11,
                               textColor=GRAY, alignment=TA_CENTER, spaceAfter=3*mm)
    s_footer = ParagraphStyle('JFooter', fontName=FONT_MINCHO, fontSize=7, leading=10,
                              textColor=GRAY, alignment=TA_CENTER)
    s_th = ParagraphStyle('JTH', fontName=FONT_GOTHIC, fontSize=8.5, leading=12,
                          textColor=WHITE, alignment=TA_CENTER)
    s_td = ParagraphStyle('JTD', fontName=FONT_MINCHO, fontSize=8.5, leading=12, textColor=DARK)
    s_tdc = ParagraphStyle('JTDc', fontName=FONT_MINCHO, fontSize=8.5, leading=12,
                           textColor=DARK, alignment=TA_CENTER)

    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )

    story = []
    page_width = A4[0] - 30*mm  # 180mm usable

    # ===== COVER =====
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph('サウンドヒーリング協会', s_title))
    story.append(Paragraph('X（Twitter）投稿コンテンツ 全90本', s_title))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width='60%', thickness=2, color=X_BLUE))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('アカウント: @SFH_Science', s_subtitle))
    story.append(Paragraph('ターゲット: 40代〜60代女性（子育てを終えた層）', s_subtitle))
    story.append(Paragraph('核心メッセージ: 病院に頼らず「自己回復力」を高める知恵', s_subtitle))
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph('NPO法人サウンドヒーリング協会 / 株式会社ジョイファンデーション', s_subtitle))
    story.append(Paragraph('作成日: 2026年3月10日', s_caption))
    story.append(PageBreak())

    # ===== TOC / OVERVIEW =====
    story.append(Paragraph('カテゴリ別一覧', s_h1))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    # Summary table
    header = [Paragraph(h, s_th) for h in ['カテゴリ', '本数', '番号範囲', '内容']]
    rows = [
        [Paragraph('科学データ・Tips', s_td), Paragraph('36本', s_tdc), Paragraph('X-001〜X-036', s_tdc),
         Paragraph('自律神経(12) / 自然音・1/fゆらぎ(12) / 自己回復力(12)', s_td)],
        [Paragraph('名言・理念', s_td), Paragraph('18本', s_tdc), Paragraph('X-037〜X-054', s_tdc),
         Paragraph('理事長メッセージ、哲学者の言葉、協会コンセプト', s_td)],
        [Paragraph('イベント告知', s_td), Paragraph('18本', s_tdc), Paragraph('X-055〜X-072', s_tdc),
         Paragraph('テンプレート形式、各イベント対応', s_td)],
        [Paragraph('記事シェア用', s_td), Paragraph('18本', s_tdc), Paragraph('X-073〜X-090', s_tdc),
         Paragraph('note/YouTube/LINE誘導、テンプレート形式', s_td)],
    ]
    data = [header] + rows
    t = Table(data, colWidths=[30*mm, 18*mm, 32*mm, 80*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), X_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), FONT_MINCHO),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDBDBD')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5*mm),
        ('BACKGROUND', (0, 1), (-1, 1), LIGHT_BLUE),
        ('BACKGROUND', (0, 2), (-1, 2), LIGHT_GREEN),
        ('BACKGROUND', (0, 3), (-1, 3), LIGHT_ORANGE),
        ('BACKGROUND', (0, 4), (-1, 4), LIGHT_PURPLE),
    ]))
    story.append(t)

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('投稿スケジュール（曜日別ルーティン）', s_h2))
    sched_header = [Paragraph(h, s_th) for h in ['曜日', 'カテゴリ', '投稿時間']]
    sched_rows = [
        ['月', '科学データ・Tips', '9:00'],
        ['火', 'イベント告知', '9:00'],
        ['水', '名言・理念', '9:00'],
        ['木', '記事シェア', '9:00'],
        ['金', '科学データ・Tips', '9:00'],
        ['土', 'イベント告知/報告', '9:00'],
        ['日', '名言・理念', '9:00'],
    ]
    sched_data = [sched_header] + [[Paragraph(c, s_tdc) for c in r] for r in sched_rows]
    st = Table(sched_data, colWidths=[30*mm, 60*mm, 30*mm])
    st.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), X_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), FONT_MINCHO),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDBDBD')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5*mm),
    ]))
    story.append(st)

    story.append(PageBreak())

    # ===== POSTS BY CATEGORY =====
    cat_colors = {
        '科学データ・Tips': LIGHT_BLUE,
        '名言・理念': LIGHT_GREEN,
        'イベント告知': LIGHT_ORANGE,
        '記事シェア用': LIGHT_PURPLE,
    }

    current_cat = ''
    current_subcat = ''

    for post in posts:
        # Category header
        if post['category'] != current_cat:
            current_cat = post['category']
            current_subcat = ''
            if current_cat == '科学データ・Tips':
                story.append(Paragraph('カテゴリ1: 科学データ・Tips（36本）', s_h1))
            elif current_cat == '名言・理念':
                story.append(PageBreak())
                story.append(Paragraph('カテゴリ2: 名言・理念（18本）', s_h1))
            elif current_cat == 'イベント告知':
                story.append(PageBreak())
                story.append(Paragraph('カテゴリ3: イベント告知テンプレート（18本）', s_h1))
            elif current_cat == '記事シェア用':
                story.append(PageBreak())
                story.append(Paragraph('カテゴリ4: 記事シェア用（18本）', s_h1))
            story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

        # Subcategory header
        if post['subcategory'] and post['subcategory'] != current_subcat:
            current_subcat = post['subcategory']
            story.append(Paragraph(current_subcat, s_h3))

        # Post box
        lines = post['content'].split('\n')
        bg = cat_colors.get(post['category'], LIGHT_BLUE)
        box = RoundedBox(page_width, lines, bg, post['code'], post['category'])
        story.append(KeepTogether([box, Spacer(1, 3*mm)]))

    # Footer
    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=GRAY))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('共通ハッシュタグ: #サウンドヒーリング #自然音 #自律神経 #リラックス #セルフケア #ウェルビーイング #癒し #健康', s_footer))
    story.append(Paragraph('作成: Claude Code / 喜田康二郎 | 2026年3月10日', s_footer))

    doc.build(story)
    print(f'PDF generated: {OUTPUT_PATH} ({len(posts)} posts)')


if __name__ == '__main__':
    build_pdf()
