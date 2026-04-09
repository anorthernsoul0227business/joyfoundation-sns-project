#!/usr/bin/env python3
"""
SNS投稿スケジュール PDF生成（3月・4月）
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import os

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
LIGHT_GREEN = HexColor('#E8F5E9')
LIGHT_BLUE = HexColor('#E3F2FD')
LIGHT_ORANGE = HexColor('#FFF3E0')
LIGHT_PURPLE = HexColor('#F3E5F5')
LIGHT_RED = HexColor('#FFEBEE')

# Platform colors
X_COLOR = HexColor('#1DA1F2')
IG_COLOR = HexColor('#E1306C')
YT_COLOR = HexColor('#FF0000')
NOTE_COLOR = HexColor('#41C9B4')
LINE_COLOR = HexColor('#06C755')

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'SNS投稿スケジュール_3月4月.pdf')


def create_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'JTitle', fontName=FONT_GOTHIC, fontSize=22, leading=30,
        textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=5*mm
    ))
    styles.add(ParagraphStyle(
        'JSubtitle', fontName=FONT_GOTHIC, fontSize=12, leading=16,
        textColor=GRAY, alignment=TA_CENTER, spaceAfter=8*mm
    ))
    styles.add(ParagraphStyle(
        'JH1', fontName=FONT_GOTHIC, fontSize=16, leading=22,
        textColor=PRIMARY, spaceBefore=6*mm, spaceAfter=4*mm
    ))
    styles.add(ParagraphStyle(
        'JH2', fontName=FONT_GOTHIC, fontSize=13, leading=18,
        textColor=SECONDARY, spaceBefore=5*mm, spaceAfter=3*mm
    ))
    styles.add(ParagraphStyle(
        'JH3', fontName=FONT_GOTHIC, fontSize=11, leading=15,
        textColor=DARK, spaceBefore=4*mm, spaceAfter=2*mm
    ))
    styles.add(ParagraphStyle(
        'JBody', fontName=FONT_MINCHO, fontSize=9.5, leading=15,
        textColor=DARK, spaceAfter=2*mm
    ))
    styles.add(ParagraphStyle(
        'JBullet', fontName=FONT_MINCHO, fontSize=9.5, leading=15,
        textColor=DARK, leftIndent=10*mm, bulletIndent=5*mm, spaceAfter=1*mm
    ))
    styles.add(ParagraphStyle(
        'JTableHeader', fontName=FONT_GOTHIC, fontSize=8, leading=11,
        textColor=WHITE, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'JTableCell', fontName=FONT_MINCHO, fontSize=8, leading=11,
        textColor=DARK
    ))
    styles.add(ParagraphStyle(
        'JTableCellCenter', fontName=FONT_MINCHO, fontSize=8, leading=11,
        textColor=DARK, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'JTableCellSmall', fontName=FONT_MINCHO, fontSize=7.5, leading=10,
        textColor=DARK
    ))
    styles.add(ParagraphStyle(
        'JCaption', fontName=FONT_GOTHIC, fontSize=8, leading=11,
        textColor=GRAY, alignment=TA_CENTER, spaceAfter=3*mm
    ))
    styles.add(ParagraphStyle(
        'JFooter', fontName=FONT_MINCHO, fontSize=7, leading=10,
        textColor=GRAY, alignment=TA_CENTER
    ))
    return styles


def make_table(headers, rows, col_widths=None, header_color=PRIMARY):
    s = create_styles()
    header_cells = [Paragraph(h, s['JTableHeader']) for h in headers]
    data = [header_cells]
    for row in rows:
        data.append([Paragraph(str(c), s['JTableCell']) for c in row])
    if col_widths is None:
        col_widths = [170*mm // len(headers)] * len(headers)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_MINCHO),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3*mm),
        ('TOPPADDING', (0, 0), (-1, 0), 2.5*mm),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2*mm),
        ('TOPPADDING', (0, 1), (-1, -1), 2*mm),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDBDBD')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
    t.setStyle(TableStyle(style_cmds))
    return t


def make_colored_table(headers, rows, col_widths, header_color, row_colors=None):
    """Table with optional per-row background colors."""
    s = create_styles()
    header_cells = [Paragraph(h, s['JTableHeader']) for h in headers]
    data = [header_cells]
    for row in rows:
        data.append([Paragraph(str(c), s['JTableCell']) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_MINCHO),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3*mm),
        ('TOPPADDING', (0, 0), (-1, 0), 2.5*mm),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2*mm),
        ('TOPPADDING', (0, 1), (-1, -1), 2*mm),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDBDBD')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    if row_colors:
        for i, color in enumerate(row_colors):
            if color:
                style_cmds.append(('BACKGROUND', (0, i+1), (-1, i+1), color))
    t.setStyle(TableStyle(style_cmds))
    return t


def build_pdf():
    s = create_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )
    story = []

    # ===== COVER =====
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph('サウンドヒーリング協会', s['JTitle']))
    story.append(Paragraph('SNS投稿スケジュール', s['JTitle']))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width='60%', thickness=2, color=PRIMARY))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('2026年 3月・4月', s['JSubtitle']))
    story.append(Paragraph('X / Instagram / YouTube / note / LINE', s['JSubtitle']))
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph('NPO法人サウンドヒーリング協会 / 株式会社ジョイファンデーション', s['JSubtitle']))
    story.append(Paragraph('作成日: 2026年3月10日', s['JCaption']))
    story.append(PageBreak())

    # ===== OVERVIEW =====
    story.append(Paragraph('全体概要', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('2ヶ月間の投稿数サマリー', s['JH2']))
    story.append(make_table(
        ['プラットフォーム', '頻度', '3月', '4月', '2ヶ月合計', '制作済み', '残り'],
        [
            ['X（Twitter）', '毎日', '22本', '30本', '52本', '90本', '38本'],
            ['Instagram', '週4回（月水金土）', '13本', '18本', '31本', '48本', '17本'],
            ['YouTube', '週2回（火金）', '6本', '8本', '14本', '24本台本', '10本'],
            ['note', '週1回（木）', '3本', '4本', '7本', '12本', '5本'],
            ['LINE', '週1回（水）', '3通', '4通', '7通', '7通', '0通'],
            ['合計', '—', '47本', '64本', '111本', '—', '—'],
        ],
        col_widths=[28*mm, 32*mm, 18*mm, 18*mm, 22*mm, 26*mm, 18*mm]
    ))

    story.append(Paragraph('曜日別ルーティン', s['JH2']))
    story.append(make_table(
        ['曜日', 'X', 'Instagram', 'YouTube', 'note', 'LINE'],
        [
            ['月', '科学データ・Tips', 'カルーセル', '—', '—', '—'],
            ['火', 'イベント告知', '—', '長尺BGM / 実践', '—', '—'],
            ['水', '名言・理念', '単画像', '—', '—', 'ステップ配信'],
            ['木', '記事シェア', '—', '—', '記事公開', '—'],
            ['金', '科学データ・Tips', 'カルーセル', '解説・教育', '—', '—'],
            ['土', 'イベント告知', 'リール / 告知', '—', '—', '—'],
            ['日', '名言・理念', '—', '—', '—', '—'],
        ],
        col_widths=[18*mm, 30*mm, 28*mm, 30*mm, 22*mm, 26*mm]
    ))
    story.append(PageBreak())

    # ===== MARCH =====
    story.append(Paragraph('3月 SNS投稿スケジュール（3/10〜3/31）', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('週別概要', s['JH2']))
    story.append(make_table(
        ['週', '期間', 'X', 'Instagram', 'YouTube', 'note', 'LINE'],
        [
            ['W1', '3/10(月)〜3/16(日)', '7本', '4本', '2本', '1本', '1本'],
            ['W2', '3/17(月)〜3/23(日)', '7本', '4本', '2本', '1本', '1本'],
            ['W3', '3/24(月)〜3/31(月)', '8本', '5本', '2本', '1本', '1本'],
            ['合計', '', '22本', '13本', '6本', '3本', '3本'],
        ],
        col_widths=[14*mm, 38*mm, 20*mm, 22*mm, 22*mm, 18*mm, 18*mm]
    ))

    # X March
    story.append(Paragraph('X（Twitter）— 毎日投稿 @SFH_Science', s['JH2']))
    x_march_rows = [
        ['3/10', '月', '科学データ', 'X-001', '体感音響実験で心拍数低下・副交感神経機能の亢進を確認'],
        ['3/11', '火', 'イベント告知', 'X-058', 'ここちよい音の日（毎月開催の無料体験会）'],
        ['3/12', '水', '名言・理念', 'X-037', '「音は心の糧である」── 喜田圭一郎理事長'],
        ['3/13', '木', '記事シェア', 'X-073', '【note更新】NOTE-001連動シェア'],
        ['3/14', '金', '科学データ', 'X-002', '自律神経の2種類（交感神経=アクセル、副交感神経=ブレーキ）'],
        ['3/15', '土', 'イベント告知', 'X-056', 'スターライトヒーリング マラマハワイ紹介'],
        ['3/16', '日', '名言・理念', 'X-038', '「心と体に自然のリズムを取り戻す」協会コンセプト'],
        ['3/17', '月', '科学データ', 'X-003', '福祉ワーカー13名・週2回15分の自然音で睡眠改善'],
        ['3/18', '火', 'イベント告知', 'X-057', 'Harmonic Day（正会員限定オンラインイベント）'],
        ['3/19', '水', '名言・理念', 'X-039', 'ゲイナー博士「音は古代から治癒力促進に使用されてきた」'],
        ['3/20', '木', '記事シェア', 'X-074', '【ブログ更新】自然音が自律神経に与える影響'],
        ['3/21', '金', '科学データ', 'X-004', '東京大学大学院の研究「音刺激で精神的ストレス低減」'],
        ['3/22', '土', 'イベント告知', 'X-059', 'Healing Garden 体験セッション（自由が丘）'],
        ['3/23', '日', '名言・理念', 'X-040', '「未病」の考え方─病気にならない体をつくる'],
        ['3/24', '月', '科学データ', 'X-005', '足底への音響刺激で自律神経機能が向上'],
        ['3/25', '火', 'イベント告知', 'X-060', 'オンラインワークショップ（初心者向け入門講座）'],
        ['3/26', '水', '名言・理念', 'X-041', '「自然界にある音はすべて意味がある」'],
        ['3/27', '木', '記事シェア', 'X-075', '【YouTube公開】YT-BGM-001連動シェア'],
        ['3/28', '金', '科学データ', 'X-006', '温泉気候医学会報告：9例中9例で心拍数低下'],
        ['3/29', '土', 'イベント告知', 'X-067', '会員募集中（正会員のメリット紹介）'],
        ['3/30', '日', '名言・理念', 'X-042', '日野原重明先生と喜田理事長の交流「音楽は人を癒す」'],
        ['3/31', '月', '科学データ', 'X-007', '人体の約70%は水分─体感音響の科学的根拠'],
    ]
    # Category colors
    cat_colors = {
        '科学データ': LIGHT_BLUE,
        'イベント告知': LIGHT_ORANGE,
        '名言・理念': LIGHT_GREEN,
        '記事シェア': LIGHT_PURPLE,
    }
    row_colors_x_mar = [cat_colors.get(r[2]) for r in x_march_rows]
    story.append(make_colored_table(
        ['日付', '曜日', 'カテゴリ', '番号', 'タイトル'],
        x_march_rows, [16*mm, 12*mm, 24*mm, 16*mm, 94*mm],
        X_COLOR, row_colors_x_mar
    ))
    story.append(Paragraph(
        '色分け: 青=科学データ / 橙=イベント告知 / 緑=名言・理念 / 紫=記事シェア', s['JCaption']
    ))
    story.append(PageBreak())

    # IG March
    story.append(Paragraph('Instagram — 週4回 @harmonicscience_jp', s['JH2']))
    story.append(make_colored_table(
        ['日付', '曜日', '形式', '番号', 'タイトル'],
        [
            ['3/10', '月', 'カルーセル', 'IG-C-001', '自律神経と自然音の関係'],
            ['3/12', '水', '単画像', 'IG-S-001', '音は環境要因（名言画像）'],
            ['3/14', '金', 'カルーセル', 'IG-C-002', 'オキシトシンと自然音'],
            ['3/15', '土', 'リール', 'IG-R-001', '1分でわかる自然音の効果'],
            ['3/17', '月', 'カルーセル', 'IG-C-003', '1/fゆらぎの秘密'],
            ['3/19', '水', '単画像', 'IG-S-002', '体は70%水分（科学図解）'],
            ['3/21', '金', 'カルーセル', 'IG-C-004', '睡眠の質を上げる自然音'],
            ['3/22', '土', 'イベント告知', 'IG-E-001', 'オンラインHarmonic Day告知'],
            ['3/24', '月', 'カルーセル', 'IG-C-005', '体感音響とは'],
            ['3/26', '水', '単画像', 'IG-S-003', '低い音は弛緩、高い音は覚醒'],
            ['3/28', '金', 'カルーセル', 'IG-C-006', '呼吸と声のヒーリング'],
            ['3/29', '土', 'リール', 'IG-R-002', '寝つきが悪い人へ（睡眠改善法）'],
            ['3/31', '月', 'カルーセル', 'IG-C-007', '水への自然音実験'],
        ],
        [16*mm, 12*mm, 24*mm, 20*mm, 90*mm],
        IG_COLOR
    ))

    # YT, note, LINE March
    story.append(Paragraph('YouTube — 週2回 @harmonicscience2651', s['JH2']))
    story.append(make_table(
        ['日付', '曜日', 'カテゴリ', '番号', 'タイトル'],
        [
            ['3/11', '火', '長尺BGM', 'YT-BGM-001', '【睡眠用BGM】森の自然音 3時間'],
            ['3/14', '金', '解説・教育', 'YT-EDU-001', 'なぜ自然音は体に良いのか？科学的に解説'],
            ['3/18', '火', '長尺BGM', 'YT-BGM-002', '【作業用BGM】小川のせせらぎ 2時間'],
            ['3/21', '金', '実践ガイド', 'YT-PRC-001', '【5分実践】自律神経を整える呼吸法'],
            ['3/25', '火', '長尺BGM', 'YT-BGM-003', '【リラックスBGM】波の音 3時間'],
            ['3/28', '金', '解説・教育', 'YT-EDU-002', '1/fゆらぎとは？心地よさの科学'],
        ],
        col_widths=[16*mm, 12*mm, 24*mm, 24*mm, 86*mm],
        header_color=YT_COLOR
    ))

    story.append(Paragraph('note — 週1回（木）', s['JH2']))
    story.append(make_table(
        ['日付', '曜日', '種類', '番号', 'タイトル'],
        [
            ['3/13', '木', '無料', 'NOTE-001', '自然音入門 ─ なぜ今、自然音が注目されているのか'],
            ['3/20', '木', '無料', 'NOTE-002', '自律神経を整える自然音の聴き方'],
            ['3/27', '木', '無料', 'NOTE-003', '体感音響とは ─ 耳だけでなく体で聴く'],
        ],
        col_widths=[16*mm, 12*mm, 16*mm, 24*mm, 94*mm],
        header_color=NOTE_COLOR
    ))

    story.append(Paragraph('LINE — 週1回（水）@868hqnfw', s['JH2']))
    story.append(make_table(
        ['日付', '曜日', '配信番号', '内容'],
        [
            ['3/12', '水', 'LINE Day0', 'あいさつ＋特典PDF「自然音入門ガイド」プレゼント'],
            ['3/19', '水', 'LINE Day1', '自己紹介＋協会紹介（3つのメソッド）'],
            ['3/26', '水', 'LINE Day2', '自然音の科学（研究データ3つ紹介）'],
        ],
        col_widths=[16*mm, 12*mm, 28*mm, 106*mm],
        header_color=LINE_COLOR
    ))

    story.append(Paragraph('3月の運用ポイント', s['JH2']))
    for item in [
        'YouTube: 最初の3週で長尺BGM動画（3時間・2時間・3時間）を集中投稿し、再生時間を稼ぐ',
        'note: 無料記事を先行公開してフォロワー獲得を優先',
        'LINE: ステップ配信の最初の3通（Day0〜Day2）で信頼構築',
        'X: 科学データ / 名言 / イベント告知 / 記事シェアの曜日別ローテーション確立',
        'Instagram: カルーセル知識系を中心に、週1本ずつ単画像・リールを交ぜてバランスよく配信',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(PageBreak())

    # ===== APRIL =====
    story.append(Paragraph('4月 SNS投稿スケジュール（4/1〜4/30）', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('4月のイベント', s['JH2']))
    story.append(make_table(
        ['日付', 'イベント', '会場', '料金'],
        [
            ['4/2-4', 'ここちよい音の日', '太陽食品世田谷店（尾山台駅3分）', '500円'],
            ['4/12', 'スターライトヒーリング マラマハワイ追加公演', 'さいたま市宇宙劇場', '大人620円'],
            ['4/14', 'オンライン講座「音のウェルビーイング」第1回', 'Zoom', '4,000円'],
            ['4/23', 'オンライン講座 第2回', 'Zoom', '4,000円'],
        ],
        col_widths=[18*mm, 58*mm, 52*mm, 24*mm],
        header_color=ACCENT
    ))

    story.append(Paragraph('イベント告知の4段階配置', s['JH2']))
    story.append(make_table(
        ['イベント', '1週間前', '3日前', '前日', '当日'],
        [
            ['ここちよい音の日(4/2-4)', '3/26(済)', '3/30', '4/1', '4/2'],
            ['マラマハワイ(4/12)', '4/5', '4/9', '4/11', '4/12'],
            ['講座 第1回(4/14)', '4/7', '4/11', '4/13', '4/14'],
            ['講座 第2回(4/23)', '4/16', '4/20', '4/22', '4/23'],
        ],
        col_widths=[40*mm, 28*mm, 28*mm, 28*mm, 28*mm],
        header_color=ACCENT
    ))

    story.append(Paragraph('週別概要', s['JH2']))
    story.append(make_table(
        ['週', '期間', 'X', 'Instagram', 'YouTube', 'note', 'LINE'],
        [
            ['W4', '4/1(火)〜4/6(日)', '6本', '4本', '2本', '1本', '1本'],
            ['W5', '4/7(月)〜4/13(日)', '7本', '4本', '2本', '1本', '1本'],
            ['W6', '4/14(月)〜4/20(日)', '7本', '4本', '2本', '1本', '1本'],
            ['W7', '4/21(月)〜4/27(日)', '7本', '4本', '2本', '1本', '1本'],
            ['W8', '4/28(月)〜4/30(水)', '3本', '2本', '0本', '0本', '0本'],
            ['合計', '', '30本', '18本', '8本', '4本', '4本'],
        ],
        col_widths=[14*mm, 38*mm, 20*mm, 22*mm, 22*mm, 18*mm, 18*mm]
    ))
    story.append(PageBreak())

    # X April
    story.append(Paragraph('X（Twitter）— 4月 毎日投稿', s['JH2']))
    x_april_rows = [
        ['4/1', '火', 'イベント告知', 'X-055', '【明日から開催】ここちよい音の日 4/2-4 太陽食品世田谷店コラボ'],
        ['4/2', '水', 'イベント告知', 'X-055', '【本日開催中】ここちよい音の日 太陽食品世田谷店 13:00〜16:00'],
        ['4/3', '木', '記事シェア', 'X-076', '【協会誌より】サウンドヒーリングの最新情報'],
        ['4/4', '金', '科学データ', 'X-008', '低い音は体に共鳴し弛緩、高い音は意識を覚醒'],
        ['4/5', '土', 'イベント告知', 'X-055', '【1週間後】マラマハワイ追加公演 4/12'],
        ['4/6', '日', '名言・理念', 'X-043', '「Harmonic Revolution」─ 調和の革命'],
        ['4/7', '月', 'イベント告知', 'X-070', '【1週間後】オンライン講座 4/14 Zoom 4,000円'],
        ['4/8', '火', '科学データ', 'X-009', 'うつ病患者62名への施術で気分改善'],
        ['4/9', '水', 'イベント告知', 'X-061', '【3日後】マラマハワイ追加公演 4/12 大人620円'],
        ['4/10', '木', '記事シェア', 'X-077', '【おすすめ記事】サウンドヒーリング入門ガイド'],
        ['4/11', '金', 'イベント告知', 'X-062', '【明日】マラマハワイ & 【3日後】オンライン講座'],
        ['4/12', '土', 'イベント告知', 'X-055', '【本日開催】マラマハワイ さいたま市宇宙劇場 13:30〜'],
        ['4/13', '日', 'イベント告知', 'X-062', '【明日開催】オンライン講座 第1回 Zoom 10:00〜12:00'],
        ['4/14', '月', 'イベント告知', 'X-070', '【本日開催】オンライン講座 第1回 10:00〜'],
        ['4/15', '火', '科学データ', 'X-010', '副交感神経が優位になると─筋肉緩和・腸管安定・呼吸深化'],
        ['4/16', '水', 'イベント告知', 'X-070', '【1週間後】オンライン講座 第2回 4/23 Zoom'],
        ['4/17', '木', '記事シェア', 'X-078', '【研究紹介】note記事で科学的根拠を詳しく解説'],
        ['4/18', '金', '科学データ', 'X-011', '5種類のリラクセーション法比較─状態不安が有意に減少'],
        ['4/19', '土', '名言・理念', 'X-044', 'ピタゴラス「宇宙は音楽である」─2500年前からの知恵'],
        ['4/20', '日', 'イベント告知', 'X-061', '【3日後】オンライン講座 第2回 4/23 Zoom'],
        ['4/21', '月', '科学データ', 'X-012', '自律神経バランスの乱れチェック─1日15分の自然音から'],
        ['4/22', '火', 'イベント告知', 'X-062', '【明日開催】オンライン講座 第2回 Zoom 10:00〜12:00'],
        ['4/23', '水', 'イベント告知', 'X-070', '【本日開催】オンライン講座 第2回 10:00〜'],
        ['4/24', '木', '記事シェア', 'X-079', '【体験談紹介】会員のサウンドヒーリング体験記'],
        ['4/25', '金', '科学データ', 'X-013', '1/fゆらぎとは─自然音が心地よい科学的理由'],
        ['4/26', '土', '名言・理念', 'X-045', '「自分を信じる時代」─自分軸を持つことの大切さ'],
        ['4/27', '日', '名言・理念', 'X-046', '「体で聴く」という体験─体感音響(Vibroacoustic)'],
        ['4/28', '月', '科学データ', 'X-014', '人工音に不快・自然音に快適─これは本能'],
        ['4/29', '火', '名言・理念', 'X-047', '「音はこれから更に社会に貢献していくだろう」'],
        ['4/30', '水', '記事シェア', 'X-080', '【実践ガイド】自宅でできる自然音の聴き方動画'],
    ]
    row_colors_x_apr = [cat_colors.get(r[2]) for r in x_april_rows]
    story.append(make_colored_table(
        ['日付', '曜日', 'カテゴリ', '番号', 'タイトル'],
        x_april_rows, [14*mm, 10*mm, 22*mm, 14*mm, 102*mm],
        X_COLOR, row_colors_x_apr
    ))
    story.append(Paragraph(
        '色分け: 青=科学データ / 橙=イベント告知 / 緑=名言・理念 / 紫=記事シェア', s['JCaption']
    ))
    story.append(PageBreak())

    # IG April
    story.append(Paragraph('Instagram — 4月 週4回', s['JH2']))
    story.append(make_colored_table(
        ['日付', '曜日', '形式', '番号', 'タイトル'],
        [
            ['4/1', '火※', 'イベント告知', 'IG-E-002', '【明日から】ここちよい音の日 太陽食品世田谷店コラボ'],
            ['4/2', '水', '単画像', 'IG-S-004', '心と体に自然のリズムを（名言画像）'],
            ['4/4', '金', 'カルーセル', 'IG-C-008', '植物と自然音の実験（48日間）'],
            ['4/5', '土', 'イベント告知', 'IG-E-003', 'マラマハワイ追加公演 4/12告知'],
            ['4/7', '月', 'カルーセル', 'IG-C-009', '骨密度と自然音（70代・80代女性の実例）'],
            ['4/9', '水', '単画像', 'IG-S-005', '自分軸を持つことの大切さ'],
            ['4/11', '金', 'リール', 'IG-R-003', '肩こりと自律神経（体感音響紹介）'],
            ['4/12', '土', 'イベント告知', 'IG-E-003', '【本日開催】マラマハワイ追加公演 レポート予告'],
            ['4/14', '月', 'カルーセル', 'IG-C-010', '現代人と人工音（音のストレス）'],
            ['4/16', '水', '単画像', 'IG-S-006', '病院に頼らない生き方'],
            ['4/18', '金', 'カルーセル', 'IG-C-011', '朝・昼・夜の自然音活用法'],
            ['4/19', '土', 'リール', 'IG-R-004', '声で自分を癒す（呼吸と声の実践）'],
            ['4/21', '月', 'カルーセル', 'IG-C-012', '更年期と自律神経'],
            ['4/23', '水', '単画像', 'IG-S-007', '呼吸を整えると心が整う'],
            ['4/25', '金', 'カルーセル', 'IG-C-013', '在宅ワークの音環境（集中力UP）'],
            ['4/26', '土', 'イベント告知', 'IG-E-004', 'Harmonic Scienceフォーラム告知'],
            ['4/28', '月', 'カルーセル', 'IG-C-014', '子育て後の自分時間（セルフケア習慣）'],
            ['4/30', '水', '単画像', 'IG-S-008', '朝5分の自然音習慣'],
        ],
        [14*mm, 12*mm, 22*mm, 20*mm, 94*mm],
        IG_COLOR
    ))

    # YT April
    story.append(Paragraph('YouTube — 4月 週2回', s['JH2']))
    story.append(make_table(
        ['日付', '曜日', 'カテゴリ', '番号', 'タイトル'],
        [
            ['4/1', '火', '長尺BGM', 'YT-BGM-004', '【睡眠用BGM】雨の音 2時間'],
            ['4/4', '金', '解説・教育', 'YT-EDU-003', '自律神経を整える3つの方法'],
            ['4/8', '火', '実践ガイド', 'YT-PRC-002', '朝の自然音ルーティン 10分'],
            ['4/11', '金', 'イベント記録', 'YT-EVT-001', 'マラマハワイ ダイジェスト'],
            ['4/15', '火', '長尺BGM', 'YT-BGM-005', '【朝の目覚め】鳥のさえずり 1時間'],
            ['4/18', '金', '解説・教育', 'YT-EDU-004', '睡眠の質を上げる自然音の使い方'],
            ['4/22', '火', '実践ガイド', 'YT-PRC-003', '寝る前の自然音ルーティン 15分'],
            ['4/25', '金', '解説・教育', 'YT-EDU-005', '体感音響とは？耳だけでなく体で聴く'],
        ],
        col_widths=[14*mm, 12*mm, 24*mm, 24*mm, 88*mm],
        header_color=YT_COLOR
    ))

    story.append(PageBreak())

    # note April
    story.append(Paragraph('note — 4月 週1回', s['JH2']))
    story.append(make_table(
        ['日付', '曜日', '種類', '番号', 'タイトル'],
        [
            ['4/3', '木', '無料', 'NOTE-004', '呼吸と声のヒーリング ─ 自分の声で自分を癒す'],
            ['4/10', '木', '無料', 'NOTE-005', '喜田圭一郎理事長が語る「Harmonic Revolution」'],
            ['4/17', '木', '有料(500円)', 'NOTE-P-001', '【実践講座1】自然音で眠る ─ 睡眠改善完全ガイド'],
            ['4/24', '木', '無料', 'NOTE-006', 'サウンドヒーリング協会の20年'],
        ],
        col_widths=[14*mm, 12*mm, 22*mm, 24*mm, 90*mm],
        header_color=NOTE_COLOR
    ))

    # LINE April
    story.append(Paragraph('LINE — 4月 週1回（水）', s['JH2']))
    story.append(make_table(
        ['日付', '曜日', '配信番号', '内容'],
        [
            ['4/2', '水', 'LINE Day3', '体感音響の紹介（3メソッド紹介）'],
            ['4/9', '水', 'LINE Day4', '体験者の声（50代・60代・40代女性の声）'],
            ['4/16', '水', 'LINE Day5', '体験会のご案内（ここちよい音の日・Harmonic Day）'],
            ['4/23', '水', 'LINE Day7', '正会員のご案内（年会費・特典紹介）'],
        ],
        col_widths=[14*mm, 12*mm, 28*mm, 108*mm],
        header_color=LINE_COLOR
    ))

    # Multi-channel event coordination
    story.append(Paragraph('イベント告知 多チャンネル連動表', s['JH2']))

    story.append(Paragraph('ここちよい音の日（4/2-4）', s['JH3']))
    story.append(make_table(
        ['段階', '日付', 'X', 'Instagram', 'LINE'],
        [
            ['前日', '4/1', 'X-055カスタム', 'IG-E-002カスタム', '—'],
            ['当日', '4/2', 'X-055カスタム', '—', 'LINE Day3で言及'],
        ],
        col_widths=[18*mm, 18*mm, 36*mm, 36*mm, 36*mm],
        header_color=ACCENT
    ))

    story.append(Paragraph('スターライトヒーリング マラマハワイ（4/12）', s['JH3']))
    story.append(make_table(
        ['段階', '日付', 'X', 'Instagram', 'YouTube'],
        [
            ['1週間前', '4/5', 'X-055カスタム', 'IG-E-003カスタム', '—'],
            ['3日前', '4/9', 'X-061カスタム', '—', '—'],
            ['前日', '4/11', 'X-062カスタム', 'IG-R-003', 'YT-EVT-001'],
            ['当日', '4/12', 'X-055カスタム', 'IG-E-003カスタム', '—'],
        ],
        col_widths=[18*mm, 18*mm, 36*mm, 36*mm, 36*mm],
        header_color=ACCENT
    ))

    # Content status
    story.append(Paragraph('コンテンツ消化状況（3月+4月 合計）', s['JH2']))
    story.append(make_table(
        ['プラットフォーム', '制作済み', '3月使用', '4月使用', '残り', '残り月数'],
        [
            ['X（90本）', '90本', '22本', '30本', '38本', '約1.5ヶ月'],
            ['Instagram（48本）', '48本', '13本', '18本', '17本', '約1ヶ月'],
            ['YouTube（24本台本）', '24本', '6本', '8本', '10本', '約1.2ヶ月'],
            ['note（12本）', '12本', '3本', '4本', '5本', '約1.2ヶ月'],
            ['LINE（7通）', '7通', '3通', '4通', '0通', '定期配信へ移行'],
        ],
        col_widths=[32*mm, 22*mm, 22*mm, 22*mm, 22*mm, 26*mm]
    ))

    story.append(Paragraph('4月の運用ポイント', s['JH2']))
    for item in [
        'イベント告知4段階: 1週間前→3日前→前日→当日をX中心に全PFで連動',
        'YouTube: 長尺BGM継続 + マラマハワイ前日にイベントダイジェスト公開',
        'note: 無料記事で基盤固め後、W3に初の有料記事（500円）投入',
        'LINE: ステップ配信Day3〜Day7完了 → 信頼構築→体験会誘導→正会員化の導線確立',
        'Instagram: カルーセル7本を軸に、リール2本・単画像4本・告知3本のバランス配信',
        '4/12 マラマハワイ当日: ストーリーズでリアルタイム発信',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=GRAY))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('作成: Claude Code / 喜田康二郎 | 2026年3月10日', s['JFooter']))

    doc.build(story)
    print(f'PDF generated: {OUTPUT_PATH}')


if __name__ == '__main__':
    build_pdf()
