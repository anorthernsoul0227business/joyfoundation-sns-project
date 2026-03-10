#!/usr/bin/env python3
"""
ミーティング議事録 PDF生成スクリプト（2026年3月10日）
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import os

# Register Japanese font
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))

FONT_GOTHIC = 'HeiseiKakuGo-W5'
FONT_MINCHO = 'HeiseiMin-W3'

# Colors
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

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'ミーティング議事録_20260310.pdf')


def create_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'JTitle', fontName=FONT_GOTHIC, fontSize=22, leading=30,
        textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=5*mm
    ))
    styles.add(ParagraphStyle(
        'JSubtitle', fontName=FONT_GOTHIC, fontSize=12, leading=16,
        textColor=GRAY, alignment=TA_CENTER, spaceAfter=10*mm
    ))
    styles.add(ParagraphStyle(
        'JH1', fontName=FONT_GOTHIC, fontSize=16, leading=22,
        textColor=PRIMARY, spaceBefore=8*mm, spaceAfter=4*mm,
    ))
    styles.add(ParagraphStyle(
        'JH2', fontName=FONT_GOTHIC, fontSize=13, leading=18,
        textColor=SECONDARY, spaceBefore=6*mm, spaceAfter=3*mm
    ))
    styles.add(ParagraphStyle(
        'JH3', fontName=FONT_GOTHIC, fontSize=11, leading=15,
        textColor=DARK, spaceBefore=4*mm, spaceAfter=2*mm
    ))
    styles.add(ParagraphStyle(
        'JBody', fontName=FONT_MINCHO, fontSize=9.5, leading=15,
        textColor=DARK, spaceAfter=2*mm, alignment=TA_JUSTIFY
    ))
    styles.add(ParagraphStyle(
        'JBullet', fontName=FONT_MINCHO, fontSize=9.5, leading=15,
        textColor=DARK, leftIndent=10*mm, bulletIndent=5*mm, spaceAfter=1*mm
    ))
    styles.add(ParagraphStyle(
        'JBullet2', fontName=FONT_MINCHO, fontSize=9, leading=14,
        textColor=GRAY, leftIndent=18*mm, bulletIndent=13*mm, spaceAfter=1*mm
    ))
    styles.add(ParagraphStyle(
        'JTableHeader', fontName=FONT_GOTHIC, fontSize=8.5, leading=12,
        textColor=WHITE, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'JTableCell', fontName=FONT_MINCHO, fontSize=8.5, leading=12,
        textColor=DARK
    ))
    styles.add(ParagraphStyle(
        'JTableCellCenter', fontName=FONT_MINCHO, fontSize=8.5, leading=12,
        textColor=DARK, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'JCaption', fontName=FONT_GOTHIC, fontSize=8, leading=11,
        textColor=GRAY, alignment=TA_CENTER, spaceAfter=3*mm
    ))
    styles.add(ParagraphStyle(
        'JFooter', fontName=FONT_MINCHO, fontSize=7, leading=10,
        textColor=GRAY, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'JHighlight', fontName=FONT_GOTHIC, fontSize=10, leading=16,
        textColor=ACCENT, spaceBefore=3*mm, spaceAfter=3*mm,
        leftIndent=5*mm, borderWidth=1, borderColor=ACCENT,
        borderPadding=5, backColor=LIGHT_ORANGE
    ))
    styles.add(ParagraphStyle(
        'JBox', fontName=FONT_MINCHO, fontSize=9.5, leading=15,
        textColor=SECONDARY, spaceBefore=2*mm, spaceAfter=2*mm,
        leftIndent=5*mm, borderWidth=1, borderColor=SECONDARY,
        borderPadding=5, backColor=LIGHT_BLUE
    ))
    return styles


def make_table(headers, rows, col_widths=None, header_color=PRIMARY):
    s = create_styles()
    header_cells = [Paragraph(h, s['JTableHeader']) for h in headers]
    data = [header_cells]
    for row in rows:
        data.append([
            Paragraph(str(c), s['JTableCell']) if i == 0
            else Paragraph(str(c), s['JTableCellCenter'])
            for i, c in enumerate(row)
        ])

    if col_widths is None:
        col_widths = [170*mm // len(headers)] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_MINCHO),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4*mm),
        ('TOPPADDING', (0, 0), (-1, 0), 3*mm),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2.5*mm),
        ('TOPPADDING', (0, 1), (-1, -1), 2.5*mm),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDBDBD')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
    t.setStyle(TableStyle(style_cmds))
    return t


def build_pdf():
    s = create_styles()

    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )

    story = []

    # ===== 表紙 =====
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph('ミーティング議事録', s['JTitle']))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width='60%', thickness=2, color=PRIMARY))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('サウンドヒーリング協会 SNS広報・オンライン講座戦略', s['JSubtitle']))
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph('日時: 2026年3月10日（火）', s['JSubtitle']))
    story.append(Paragraph('参加者: 喜田圭一郎（理事長）・喜田康二郎', s['JSubtitle']))
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph('ソース: NotebookLM音声録音（新規録音100.m4a）', s['JCaption']))
    story.append(Paragraph('+ 圭一郎氏メール（kita@h-garden.com 2026/3/10 13:41）', s['JCaption']))

    story.append(PageBreak())

    # ===== 目次 =====
    story.append(Paragraph('目次', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 3*mm))
    for item in [
        '1. 決定事項サマリー',
        '2. ターゲット設定',
        '3. オンライン講座の設計',
        '4. 集客ファネル（導線設計）',
        '5. SNS運用方針',
        '6. YouTube・コンテンツ戦略',
        '7. 将来展開（海外・収益モデル）',
        '8. 講座名称（確定案）',
        '9. 次のアクション',
    ]:
        story.append(Paragraph(item, s['JBody']))
    story.append(PageBreak())

    # ===== 1. 決定事項サマリー =====
    story.append(Paragraph('1. 決定事項サマリー', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph(
        '本ミーティングでは、サウンドヒーリング協会のオンライン講座立ち上げと'
        'SNS集客の具体的な方針が議論・決定された。'
        '以下が主要な決定事項である。',
        s['JBody']
    ))

    story.append(make_table(
        ['項目', '決定内容'],
        [
            ['ターゲット', '30代〜50代の主婦層（看護関連含む）'],
            ['講座形式', 'Zoomオンライン体験会'],
            ['講座時間帯', '午前10:00〜12:00（火曜・木曜）'],
            ['価格', '4,000円/回'],
            ['定員', '6〜10名'],
            ['講座名（案）', 'Harmonic Science 入門講座 / 体験講座'],
            ['SNS発信', 'Instagram + note 同時開始、LINE公式活用'],
            ['YouTube', '自然音を無料配信、既存チャンネル活用'],
            ['収益導線', 'SNS → LINE → オンライン体験 → リアル研修 → 資格認定'],
            ['海外展開', '英語版ワークショップを将来的に検討'],
        ],
        col_widths=[40*mm, 113*mm]
    ))

    story.append(PageBreak())

    # ===== 2. ターゲット設定 =====
    story.append(Paragraph('2. ターゲット設定', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('2.1 メインターゲットの変更', s['JH2']))
    story.append(make_table(
        ['', '旧（従来）', '新（本ミーティング）'],
        [
            ['年齢層', '40代〜60代', '30代〜50代'],
            ['属性', '子育てを終えた女性', '主婦層（子育て中含む）'],
            ['拡張ターゲット', '—', '看護関連の方も含む'],
        ],
        col_widths=[35*mm, 59*mm, 59*mm]
    ))

    story.append(Paragraph('2.2 ターゲットの特徴・ニーズ', s['JH2']))
    for item in [
        '自分自身と家族の健康に関心が高い',
        '病院に頼らず「自己回復力」を高めたい',
        '午前中（10:00〜12:00）に参加しやすい時間帯がある',
        '4,000円程度なら気軽に参加を決断できる価格帯',
        '家庭で実践できる健康法を求めている',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(PageBreak())

    # ===== 3. オンライン講座 =====
    story.append(Paragraph('3. オンライン講座の設計', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('3.1 講座基本設計', s['JH2']))
    story.append(make_table(
        ['項目', '内容', '備考'],
        [
            ['形式', 'Zoomオンライン', '全国から参加可能'],
            ['時間帯', '午前10:00〜12:00（2時間）', 'ChatGPT提案、主婦層に最適'],
            ['曜日', '火曜日・木曜日', '要検証（実際の反応を見て調整）'],
            ['定員', '6〜10名', '少人数で質の高い体験を提供'],
            ['頻度', '月1回以上', '需要に応じて増回検討'],
        ],
        col_widths=[30*mm, 60*mm, 63*mm]
    ))

    story.append(Paragraph('3.2 価格設定の根拠', s['JH2']))
    story.append(Paragraph(
        '他の講座との比較検討および参加障壁のバランスから、4,000円に決定。',
        s['JBody']
    ))
    story.append(make_table(
        ['価格帯', '評価', '理由'],
        [
            ['3,000円', '低すぎる', '信頼度が薄れる（安すぎると価値を感じにくい）'],
            ['4,000円', '最適', '主婦層が参加を決断しやすく、信頼性も保てるライン'],
            ['5,000円', 'やや高い', '主婦層がすぐに結論を出しにくい'],
            ['10,000円', '高すぎる', '参考事例: 相田先生の4時間講座（1万円）→参加者2名程度'],
        ],
        col_widths=[25*mm, 30*mm, 98*mm]
    ))

    story.append(Paragraph(
        '※相田先生の講座（4時間・1万円）では参加者が2名程度にとどまっている実例あり。',
        s['JCaption']
    ))

    story.append(Paragraph('3.3 講座内容（想定）', s['JH2']))
    for item in [
        '自然音を実際に聴く体験',
        '音の健康法（ウェルビーイングメソッド）の基礎解説',
        '呼吸法の実践',
        '参加者同士の共有・質疑応答',
        '次のステップ（リアル研修・資格講座）の案内',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(Paragraph('3.4 既存講座との位置づけ', s['JH2']))
    story.append(Paragraph(
        'オンライン体験会は、既存の高額研修（ファシリテーター資格認定：10万円）への入り口として位置づける。'
        '興味を持った方がリアル体験会やワークショップを経て、最終的にプロのセラピスト・指導者を目指す導線を構築する。',
        s['JBody']
    ))

    # ファネル図
    funnel_data = [
        ['ステージ', '内容', '価格'],
        ['Step 1', 'SNS（Instagram/note/YouTube）で認知', '無料'],
        ['Step 2', 'LINE公式に友達登録', '無料（特典あり）'],
        ['Step 3', 'Zoomオンライン体験会', '4,000円'],
        ['Step 4', 'リアル体験会・ワークショップ', '—（月1回開催）'],
        ['Step 5', 'ファシリテーター資格認定研修', '100,000円'],
        ['Step 6', 'プロセラピスト・指導者コース', '上位講座'],
    ]
    funnel_table = Table(
        [[Paragraph(c, s['JTableCell']) for c in row] for row in funnel_data],
        colWidths=[25*mm, 80*mm, 48*mm]
    )
    funnel_style = [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), FONT_MINCHO),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDBDBD')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5*mm),
        ('BACKGROUND', (0, 1), (-1, 1), HexColor('#E8F5E9')),
        ('BACKGROUND', (0, 2), (-1, 2), HexColor('#C8E6C9')),
        ('BACKGROUND', (0, 3), (-1, 3), HexColor('#A5D6A7')),
        ('BACKGROUND', (0, 4), (-1, 4), HexColor('#81C784')),
        ('BACKGROUND', (0, 5), (-1, 5), HexColor('#66BB6A')),
        ('BACKGROUND', (0, 6), (-1, 6), HexColor('#4CAF50')),
    ]
    funnel_table.setStyle(TableStyle(funnel_style))
    story.append(Spacer(1, 3*mm))
    story.append(funnel_table)

    story.append(PageBreak())

    # ===== 4. 集客ファネル =====
    story.append(Paragraph('4. 集客ファネル（導線設計）', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('4.1 Instagram → LINE → オンライン講座の流れ', s['JH2']))
    story.append(Paragraph(
        'Instagramで興味を持った人を協会のホームページ経由でLINE公式に誘導し、'
        'オンライン体験会への申し込みにつなげる。',
        s['JBody']
    ))

    story.append(Paragraph('4.2 LINE公式アカウントの活用', s['JH2']))
    story.append(Paragraph('友達登録後のオートメッセージフロー:', s['JBody']))
    for item in [
        '登録直後: 挨拶メッセージ + 特典配布',
        '特典例: 30秒ヒーリングサウンド音源、科学データまとめPDF',
        'LINE登録者限定のYouTube動画リンクを配信',
        '申し込みプラットフォーム（イベントページ等）へのリンクを設置',
        '定期的に情報配信 →「無料セミナーやりませんか」等の案内',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(Paragraph('4.3 既存の体験会・イベント', s['JH2']))
    story.append(make_table(
        ['イベント', '頻度', '場所', '状況'],
        [
            ['ここちよい音の日', '毎月1回（土曜）', 'Healing Garden（自由が丘）', '4月は満席'],
            ['小田先生の体験会', '月1回', '長府の整形外科', '継続開催中'],
            ['太陽フーズコラボ体験会', '不定期', '小山大店', '企画進行中'],
            ['Zoomオンライン体験会', '月1回〜', 'オンライン', '新規立ち上げ'],
        ],
        col_widths=[42*mm, 25*mm, 52*mm, 34*mm]
    ))

    story.append(Paragraph(
        '※4月のリアルワークショップは既に満席。'
        '協会会員以外の方にどうメソッドを知っていただくかが課題であり、'
        'オンライン講座はその解決策として位置づけられる。',
        s['JBox']
    ))

    story.append(PageBreak())

    # ===== 5. SNS運用方針 =====
    story.append(Paragraph('5. SNS運用方針', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('5.1 同時発信の方針', s['JH2']))
    story.append(Paragraph(
        'ミーティングにて「やらない理由がない」として、'
        'Instagram・note・LINE を同時並行で運用開始することが決定。',
        s['JBody']
    ))

    story.append(make_table(
        ['プラットフォーム', '役割', '運用方針'],
        [
            ['Instagram', '認知・興味喚起', 'ビジュアル重視の投稿、リール活用、CTA設置'],
            ['note', '深い情報発信', '無料記事で集客 + 有料記事（1,500円程度）で収益化'],
            ['LINE公式', '見込み客育成', '友達登録 → オートメッセージ → 特典 → 申込誘導'],
            ['YouTube', '無料コンテンツ配信', '自然音BGM無料配信、Harmonic Scienceチャンネル活用'],
            ['X (Twitter)', '日常的な発信', '科学データ・Tips・イベント告知を毎日投稿'],
        ],
        col_widths=[35*mm, 35*mm, 83*mm]
    ))

    story.append(Paragraph('5.2 YouTubeチャンネル活用', s['JH2']))
    story.append(Paragraph(
        '既存の2チャンネルを活用:',
        s['JBody']
    ))
    for item in [
        'Harmonic Science チャンネル（メイン）',
        'Living Nature Sound チャンネル（自然音専用）',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(Paragraph(
        '自然音を無料で配信しつつ、オンライン講座を有料で提供。'
        '講座参加者には自分で音を聴けるコンテンツ（月額課金30〜40円程度）も将来的に検討。',
        s['JBody']
    ))

    story.append(PageBreak())

    # ===== 6. YouTube・コンテンツ戦略 =====
    story.append(Paragraph('6. YouTube・コンテンツ戦略', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('6.1 無料 → 有料の段階設計', s['JH2']))

    story.append(make_table(
        ['段階', 'コンテンツ', '価格', '目的'],
        [
            ['無料', 'YouTube自然音BGM', '0円', '認知拡大・ファン獲得'],
            ['無料', 'Instagram投稿・リール', '0円', '興味喚起・LINE誘導'],
            ['無料', 'note無料記事', '0円', '信頼構築・SEO'],
            ['有料', 'Zoomオンライン体験会', '4,000円', '体験・コミュニティ'],
            ['有料', 'note有料記事', '1,500円程度', '深い知識・収益'],
            ['有料', 'リアル研修・ワークショップ', '要確認', '本格的な学び'],
            ['有料', '資格認定研修', '100,000円', 'プロ育成'],
        ],
        col_widths=[18*mm, 48*mm, 32*mm, 55*mm]
    ))

    story.append(Paragraph('6.2 NotebookLM活用', s['JH2']))
    story.append(Paragraph(
        'ChatGPTでのトーク内容をNotebookLMに読み込ませ、戦略の整理・分析に活用。'
        '音声録音をそのまま読み込ませて文字起こし・要約が可能。'
        '今後もミーティング内容の記録・分析にNotebookLMを活用していく方針。',
        s['JBody']
    ))

    story.append(PageBreak())

    # ===== 7. 将来展開 =====
    story.append(Paragraph('7. 将来展開（海外・収益モデル）', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('7.1 海外展開', s['JH2']))
    story.append(Paragraph(
        'アメリカ等の海外向けにワークショップを英語版で実施する構想あり。'
        '「Harmonic Healing Workshop」「Sound Wellbeing」等の名称で'
        '同じ形式のオンライン講座を英語で提供することを将来的に検討。',
        s['JBody']
    ))

    story.append(Paragraph('7.2 収益モデル全体像', s['JH2']))
    story.append(make_table(
        ['収益源', '想定単価', '対象', '時期'],
        [
            ['Zoomオンライン体験会', '4,000円/回', '30-50代主婦層', '即時開始可能'],
            ['note有料記事・マガジン', '1,500円/本', 'SNSフォロワー', '即時開始可能'],
            ['YouTube広告収益', '変動', '一般視聴者', '収益化条件達成後'],
            ['リアル体験会', '要設定', '地域住民', '既に開催中'],
            ['ファシリテーター研修', '100,000円', '本格的な学習者', '既存プログラム'],
            ['セラピスト・指導者研修', '上位価格', '資格取得希望者', '既存プログラム'],
            ['英語版ワークショップ', '未定', '海外（アメリカ等）', '将来'],
        ],
        col_widths=[42*mm, 30*mm, 38*mm, 43*mm]
    ))

    story.append(PageBreak())

    # ===== 8. 講座名称 =====
    story.append(Paragraph('8. 講座名称（確定案）', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph(
        '圭一郎氏のメール（2026年3月10日 13:41）にて、'
        'ChatGPTとの検討を経た講座名称の案が共有された。',
        s['JBody']
    ))

    story.append(Spacer(1, 5*mm))

    # 講座名A
    name_a = [
        [Paragraph('<b>案A</b>', s['JTableCell']),
         Paragraph('<b>Harmonic Science 入門講座</b>', s['JTableCell'])],
        [Paragraph('サブタイトル', s['JTableCell']),
         Paragraph('世界の自然音と呼吸で整えるセルフケア', s['JTableCell'])],
        [Paragraph('想定用途', s['JTableCell']),
         Paragraph('初めての方向け、入門的な位置づけ', s['JTableCell'])],
    ]
    t_a = Table(name_a, colWidths=[35*mm, 118*mm])
    t_a.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDBDBD')),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GREEN),
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), FONT_MINCHO),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_a)

    story.append(Spacer(1, 5*mm))

    # 講座名B
    name_b = [
        [Paragraph('<b>案B</b>', s['JTableCell']),
         Paragraph('<b>Harmonic Science 体験講座</b>', s['JTableCell'])],
        [Paragraph('サブタイトル', s['JTableCell']),
         Paragraph('自然の音と声で整える健康メソッド', s['JTableCell'])],
        [Paragraph('想定用途', s['JTableCell']),
         Paragraph('体験重視、実際に音を聴く・声を出す実践型', s['JTableCell'])],
    ]
    t_b = Table(name_b, colWidths=[35*mm, 118*mm])
    t_b.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BDBDBD')),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BLUE),
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), FONT_MINCHO),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_b)

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        '※どちらの名称を採用するか、またはサブタイトルの組み合わせ変更等は今後検討。',
        s['JCaption']
    ))

    story.append(PageBreak())

    # ===== 9. 次のアクション =====
    story.append(Paragraph('9. 次のアクション', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('9.1 即時対応（優先度: 高）', s['JH2']))
    story.append(make_table(
        ['#', 'タスク', '担当', '期限目安'],
        [
            ['1', 'オンライン講座の詳細設計（カリキュラム・時間配分）', '圭一郎 + 康二郎', '3月中'],
            ['2', '講座名の最終決定', '圭一郎', '3月中'],
            ['3', 'Zoom有料講座の申込プラットフォーム構築', '康二郎', '3月中'],
            ['4', 'Instagram + note 同時発信開始', '康二郎（AI活用）', '即時'],
            ['5', 'LINE公式アカウントのオートメッセージ設定', '康二郎', '3月中'],
            ['6', 'LINE登録特典（30秒ヒーリングサウンド等）の準備', '圭一郎（音源）', '3月中'],
        ],
        col_widths=[8*mm, 75*mm, 40*mm, 30*mm]
    ))

    story.append(Paragraph('9.2 継続対応（優先度: 中）', s['JH2']))
    story.append(make_table(
        ['#', 'タスク', '担当', '期限目安'],
        [
            ['7', 'YouTube自然音コンテンツの追加配信', '圭一郎（音源）+ 康二郎', '4月〜'],
            ['8', 'オンライン講座のテスト開催（初回）', '圭一郎', '4月'],
            ['9', 'SNS広告テスト（Instagram少額広告）', '康二郎', '5月〜'],
            ['10', '英語版ワークショップの企画検討', '圭一郎 + 康二郎', '将来'],
        ],
        col_widths=[8*mm, 75*mm, 40*mm, 30*mm]
    ))

    story.append(Paragraph('9.3 圭一郎氏への依頼事項（前回から継続）', s['JH2']))
    story.append(make_table(
        ['#', '依頼内容', '状態'],
        [
            ['A', 'Facebookページに康二郎を管理者として追加', '未完了'],
            ['B', '@harmonicscience_jp とFacebookページの接続', '未完了'],
            ['C', 'LINE公式アカウント管理画面のログイン情報共有', '未完了'],
            ['D', 'X APIクレジット購入の判断（最低$5〜）', '未完了'],
        ],
        col_widths=[8*mm, 105*mm, 40*mm]
    ))

    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=GRAY))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        '本議事録は2026年3月10日のミーティング音声録音および圭一郎氏のメールに基づき作成。',
        s['JFooter']
    ))
    story.append(Paragraph('作成: Claude Code / 喜田康二郎', s['JFooter']))

    doc.build(story)
    print(f'PDF generated: {OUTPUT_PATH}')


if __name__ == '__main__':
    build_pdf()
