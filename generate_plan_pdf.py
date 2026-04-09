#!/usr/bin/env python3
"""
サウンドヒーリング協会 SNS広報・集客 6ヶ月プラン PDF生成スクリプト
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem
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
PRIMARY = HexColor('#2E7D32')       # Green
SECONDARY = HexColor('#1565C0')     # Blue
ACCENT = HexColor('#E65100')        # Orange
DARK = HexColor('#212121')
GRAY = HexColor('#616161')
LIGHT_GRAY = HexColor('#F5F5F5')
WHITE = HexColor('#FFFFFF')
LIGHT_GREEN = HexColor('#E8F5E9')
LIGHT_BLUE = HexColor('#E3F2FD')
LIGHT_ORANGE = HexColor('#FFF3E0')

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'NotebookLM_アップロード用', 'SNS広報集客6ヶ月プラン.pdf')

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
        borderWidth=0, borderPadding=0,
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
        'JBodySmall', fontName=FONT_MINCHO, fontSize=8.5, leading=13,
        textColor=DARK, spaceAfter=1*mm
    ))
    styles.add(ParagraphStyle(
        'JBullet', fontName=FONT_MINCHO, fontSize=9.5, leading=15,
        textColor=DARK, leftIndent=10*mm, bulletIndent=5*mm, spaceAfter=1*mm
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
    return styles

def make_table(headers, rows, col_widths=None, header_color=PRIMARY):
    s = create_styles()
    header_cells = [Paragraph(h, s['JTableHeader']) for h in headers]
    data = [header_cells]
    for row in rows:
        data.append([Paragraph(str(c), s['JTableCell']) if i == 0 else Paragraph(str(c), s['JTableCellCenter']) for i, c in enumerate(row)])

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
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    s = create_styles()

    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )

    story = []

    # ===== COVER =====
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph('サウンドヒーリング協会', s['JTitle']))
    story.append(Paragraph('SNS広報・集客 6ヶ月プラン', s['JTitle']))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width='60%', thickness=2, color=PRIMARY))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('2026年3月〜2026年8月', s['JSubtitle']))
    story.append(Paragraph('NPO法人サウンドヒーリング協会 / 株式会社ジョイファンデーション', s['JSubtitle']))
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph('作成日: 2026年3月6日', s['JCaption']))
    story.append(Paragraph('Version 1.0', s['JCaption']))

    story.append(PageBreak())

    # ===== TABLE OF CONTENTS =====
    story.append(Paragraph('目次', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 3*mm))
    toc_items = [
        '1. プロジェクト概要',
        '2. 現状分析と課題',
        '3. 6ヶ月ロードマップ',
        '4. プラットフォーム別戦略',
        '5. コンテンツ制作計画',
        '6. 集客ファネル設計',
        '7. 技術インフラ（自動投稿システム）',
        '8. 月別アクションプラン',
        '9. KPI・目標設定',
        '10. 必要タスク一覧',
        '11. リスクと対策',
        '12. 予算概算',
    ]
    for item in toc_items:
        story.append(Paragraph(item, s['JBody']))
    story.append(PageBreak())

    # ===== 1. PROJECT OVERVIEW =====
    story.append(Paragraph('1. プロジェクト概要', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('1.1 団体概要', s['JH2']))
    story.append(Paragraph(
        'NPO法人サウンドヒーリング協会（2001年設立）と株式会社ジョイファンデーション（1993年設立、代表: 喜田圭一郎）の2団体による共同プロジェクト。'
        '自然音・体感音響・呼吸と声の3つのメソッドを軸に、「心と体に自然のリズムを取り戻す Harmonic Revolution」をコンセプトとして活動。',
        s['JBody']
    ))

    story.append(Paragraph('1.2 プロジェクトの目的', s['JH2']))
    story.append(Paragraph(
        'SNSを活用した認知拡大・集客・収益化を実現し、サウンドヒーリングの実践者（セラピスト）を増やすことを最終目標とする。',
        s['JBody']
    ))
    for item in [
        '認知拡大: サウンドヒーリングの科学的根拠と実績を広く発信',
        '集客: 体験会・イベントへの参加者獲得、LINE登録者の増加',
        '収益化: note有料記事・YouTube収益化・体験会参加費による月15万円目標',
        '人材育成: 資格認定セラピストの養成パイプライン構築',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(Paragraph('1.3 ターゲット', s['JH2']))
    story.append(Paragraph(
        'メインターゲット: 40代〜60代女性（子育てを終えた層）。健康意識が高く、薬に頼らない自己回復力に関心がある。'
        '睡眠の質改善・ストレス解消・自律神経の乱れに悩む人。',
        s['JBody']
    ))

    story.append(Paragraph('1.4 コアメッセージ', s['JH2']))
    story.append(Paragraph(
        '「病院に頼らず、自分の力で心と体を整える」— 科学的エビデンスに基づくサウンドヒーリングで、自己回復力を高める。'
        '25年以上の活動実績、医療関係者のバックアップ、訴訟・事故ゼロの安全性を前面に。',
        s['JBody']
    ))

    story.append(PageBreak())

    # ===== 2. CURRENT STATUS =====
    story.append(Paragraph('2. 現状分析と課題', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('2.1 開設済みアカウント', s['JH2']))
    story.append(make_table(
        ['プラットフォーム', 'アカウント', '状態', 'フォロワー'],
        [
            ['X (Twitter)', '@SFH_Science', '開設済み・未投稿', '0'],
            ['Instagram', '@harmonicscience_jp', 'ビジネスアカウント', '0'],
            ['YouTube', '@harmonicscience2651', 'チャンネル作成済み', '0'],
            ['note', 'サウンドヒーリング協会', 'アカウント開設済み', '0'],
            ['LINE公式', '@868hqnfw', '開設済み', '0'],
            ['Facebook（既存）', 'harmonicscience', '運用中', '601'],
        ],
        col_widths=[38*mm, 45*mm, 45*mm, 25*mm]
    ))

    story.append(Paragraph('2.2 制作済みコンテンツ', s['JH2']))
    story.append(make_table(
        ['種別', '本数', '状態', '備考'],
        [
            ['X投稿', '90本', '下書き完了', 'YAML変換済み（自動投稿対応）'],
            ['Instagram投稿', '48本', '下書き完了', '13本YAML変換済み'],
            ['note記事', '12本', '下書き完了', '無料8本・有料4本'],
            ['YouTube台本', '24本', '下書き完了', '動画撮影・編集未着手'],
            ['LINEステップ配信', '7通', '下書き完了', '登録〜7日目自動配信'],
        ],
        col_widths=[35*mm, 20*mm, 30*mm, 68*mm]
    ))

    story.append(Paragraph('2.3 技術基盤', s['JH2']))
    story.append(make_table(
        ['項目', '状態', '詳細'],
        [
            ['自動投稿システム', 'コード実装済み', 'TypeScript / Node.js / Cloudflare Workers'],
            ['X API', '開発者登録完了・キー未取得', 'Developer Console障害中'],
            ['Instagram API', 'コード実装済み・認証未設定', 'Facebookページ接続が必要'],
            ['LINE API', 'コード実装済み・認証未設定', '管理画面ログイン情報確認待ち'],
            ['GitHub Actions', '未設定', '定期実行スケジューラー'],
        ],
        col_widths=[38*mm, 42*mm, 73*mm]
    ))

    story.append(Paragraph('2.4 主な課題', s['JH2']))
    for item in [
        'API認証情報の取得が未完了（X / Instagram / LINE全て）',
        'InstagramはFacebookページとの接続が必要（圭一郎氏の協力が必要）',
        'LINE公式アカウントの管理画面ログイン情報が不明',
        'YouTube動画の撮影・編集体制が未構築',
        '画像・サムネイル制作のリソース不足',
        '「サウンドヒーリング」が怪しいと思われがちなブランディング課題',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(PageBreak())

    # ===== 3. ROADMAP =====
    story.append(Paragraph('3. 6ヶ月ロードマップ', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(make_table(
        ['月', 'フェーズ', '主要アクション', '目標'],
        [
            ['Month 1\n(3月)', '基盤構築', 'API設定完了\nX・Instagram投稿開始\nnote初回記事公開', 'X: 50フォロワー\nIG: 100フォロワー'],
            ['Month 2\n(4月)', '運用安定化', '全プラットフォーム定期投稿\nYouTube初動画公開\nLINEステップ配信開始', 'X: 150\nIG: 300\nLINE: 50'],
            ['Month 3\n(5月)', '成長加速', '広告テスト開始\nコラボ・相互紹介\n体験会集客強化', 'X: 300\nIG: 600\nYT: 200'],
            ['Month 4\n(6月)', '体験会誘導', 'イベント告知強化\nリール動画量産\nnote有料記事本格化', 'X: 500\nIG: 1,000\nnote売上3万円'],
            ['Month 5\n(7月)', 'コミュニティ', 'ファンコミュニティ構築\nUGC促進\nメルマガ的LINE活用', 'LINE: 200\nYT: 400\n体験会月10名'],
            ['Month 6\n(8月)', '収益化確立', 'YouTube収益化申請\n有料コンテンツ拡充\n資格講座告知開始', 'YT: 500\n月収15万円\n資格問合せ5件'],
        ],
        col_widths=[22*mm, 28*mm, 58*mm, 45*mm]
    ))

    story.append(PageBreak())

    # ===== 4. PLATFORM STRATEGIES =====
    story.append(Paragraph('4. プラットフォーム別戦略', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    # X
    story.append(Paragraph('4.1 X（Twitter）— @SFH_Science', s['JH2']))
    story.append(Paragraph('役割: 日常的な情報発信・認知拡大・トラフィック送客', s['JBody']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['投稿頻度', '毎日1投稿（9:00 JST）'],
            ['コンテンツ分類', '科学データ・Tips（36本）/ 名言・哲学（18本）/ イベント告知（18本）/ シェア促進（18本）'],
            ['ハッシュタグ戦略', '#サウンドヒーリング #自然音 #自律神経 #睡眠改善 #瞑想 他'],
            ['送客先', 'note記事 / YouTube動画 / LINE登録 / イベントページ'],
            ['自動投稿', 'sns-auto-posterで完全自動化予定（YAML → API → 投稿）'],
            ['エンゲージメント', 'リプライ対応・引用RT・関連アカウントとの交流'],
        ],
        col_widths=[30*mm, 123*mm]
    ))

    # Instagram
    story.append(Paragraph('4.2 Instagram — @harmonicscience_jp', s['JH2']))
    story.append(Paragraph('役割: ビジュアル訴求・教育コンテンツ・ブランド構築', s['JBody']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['投稿頻度', '週4回（月・水・金・土 12:00 JST）'],
            ['コンテンツ分類', 'カルーセル知識系（20本）/ 単画像名言・Tips（15本）/ リール動画（8本）/ イベント告知（5本）'],
            ['カルーセル', '5枚構成: 表紙 → 症状共感 → 科学データ → メカニズム → CTA'],
            ['リール', '15-60秒の短尺動画（呼吸法実演、自然音体験、ビフォーアフター）'],
            ['CTA設計', 'LINE登録（無料PDF）/ note記事誘導 / 体験会告知'],
            ['ストーリーズ', '日常の協会活動・イベント裏側・アンケート・カウントダウン'],
        ],
        col_widths=[30*mm, 123*mm]
    ))

    # YouTube
    story.append(Paragraph('4.3 YouTube — @harmonicscience2651', s['JH2']))
    story.append(Paragraph('役割: 長尺コンテンツ・SEO流入・収益化', s['JBody']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['投稿頻度', '週2本'],
            ['カテゴリ', '自然音BGM長尺（6本）/ 解説・教育（8本）/ 実践ガイド（6本）/ イベント記録（4本）'],
            ['BGM動画', '1〜3時間の長尺。睡眠用・作業用・瞑想用。再生時間稼ぎの主力'],
            ['解説動画', '8-20分。科学データ、メソッド解説、専門家インタビュー'],
            ['収益化条件', '登録者1,000人 + 年間総再生4,000時間 → Month 4-6で申請目標'],
            ['SEO戦略', 'タイトル最適化・タグ・説明文・サムネイル・再生リスト整備'],
        ],
        col_widths=[30*mm, 123*mm]
    ))

    # note
    story.append(Paragraph('4.4 note', s['JH2']))
    story.append(Paragraph('役割: 長文コンテンツ・SEO・有料記事収益', s['JBody']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['投稿頻度', '週1本'],
            ['無料記事（8本）', '入門系・体験談・科学解説 → 集客・信頼構築'],
            ['有料記事（4本）', '実践メソッド詳細・セルフケアプログラム → 収益化（500〜1,500円）'],
            ['マガジン', '「サウンドヒーリング実践ガイド」（月額980円）を検討'],
            ['送客元', 'X・Instagram・YouTubeから誘導'],
            ['目標', 'Month 3: 月3万円 → Month 6: 月5万円'],
        ],
        col_widths=[30*mm, 123*mm]
    ))

    # LINE
    story.append(Paragraph('4.5 LINE公式 — @868hqnfw', s['JH2']))
    story.append(Paragraph('役割: 見込み客育成・イベント告知・会員化', s['JBody']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['配信頻度', '週1回 + ステップ配信（登録後7日間自動）'],
            ['ステップ配信', 'Day0: 登録ボーナスPDF / Day1: 協会紹介 / Day2-4: メソッド解説 / Day5: 体験会招待 / Day7: 正会員案内'],
            ['登録特典', '「自然音入門ガイド」PDF（12ページ）'],
            ['リッチメニュー', 'イベント情報 / 無料体験 / 会員登録 / YouTube / お問い合わせ'],
            ['セグメント配信', '興味関心別（睡眠・ストレス・瞑想・資格）に分けて配信'],
            ['目標', 'Month 3: 100登録 → Month 6: 300登録 → 体験会転換率20%'],
        ],
        col_widths=[30*mm, 123*mm]
    ))

    story.append(PageBreak())

    # ===== 5. CONTENT PLAN =====
    story.append(Paragraph('5. コンテンツ制作計画', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('5.1 制作済みコンテンツ活用', s['JH2']))
    story.append(Paragraph(
        '既に3ヶ月分（181本+LINE7通）のコンテンツ下書きが完了。これを以下のフローで活用する:',
        s['JBody']
    ))
    for item in [
        'X投稿90本 → YAML変換済み → 自動投稿システムで3ヶ月間毎日投稿',
        'Instagram48本 → 画像制作後 → 週4回投稿（一部自動化）',
        'note12本 → 校正・画像追加後 → 週1回手動公開',
        'YouTube24本 → 撮影・編集後 → 週2回公開',
        'LINE7通 → ステップ配信設定 → 登録者に自動配信',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(Paragraph('5.2 コンテンツカレンダー（月別）', s['JH2']))
    story.append(make_table(
        ['月', 'X', 'Instagram', 'YouTube', 'note', 'LINE'],
        [
            ['3月', '30本', '12本', '4本', '4本', '週1+ステップ'],
            ['4月', '30本', '16本', '8本', '4本', '週1'],
            ['5月', '30本', '16本', '8本', '4本', '週1'],
            ['6月', '30本', '16本', '8本', '4本', '週1'],
            ['7月', '30本', '16本', '8本', '4本', '週1'],
            ['8月', '30本', '16本', '8本', '4本', '週1'],
            ['合計', '180本', '92本', '44本', '24本', '26通'],
        ],
        col_widths=[20*mm, 28*mm, 28*mm, 28*mm, 28*mm, 28*mm]
    ))
    story.append(Paragraph('※3月分は制作済み。4月以降は追加制作が必要。', s['JCaption']))

    story.append(Paragraph('5.3 コンテンツ5大カテゴリ', s['JH2']))
    story.append(make_table(
        ['カテゴリ', '内容例', '対象PF', '目的'],
        [
            ['科学・エビデンス', '自律神経データ、骨密度研究、大学論文', '全PF', '信頼性構築'],
            ['哲学・理念', '理事長メッセージ、Harmonic Revolution', 'X, note', 'ブランド深化'],
            ['実践・Tips', '呼吸法、聴き方のコツ、朝の習慣', 'IG, YT', '行動促進'],
            ['イベント', '体験会告知、ハワイイベント、セミナー', '全PF', '集客'],
            ['ストーリー', '体験者の声、セラピスト紹介', 'IG, note', '共感・信頼'],
        ],
        col_widths=[32*mm, 50*mm, 25*mm, 46*mm]
    ))

    story.append(Paragraph('5.4 画像・動画制作', s['JH2']))
    story.append(make_table(
        ['種別', '必要数', '制作方法', '優先度'],
        [
            ['Instagramカルーセル画像', '100枚（5枚×20本）', 'Canva / Figma', '高'],
            ['Instagram単画像', '15枚', 'Canva テンプレート', '高'],
            ['YouTubeサムネイル', '24枚', 'Canva / Photoshop', '中'],
            ['YouTube BGM動画', '6本（1-3時間）', '自然音源 + 静止画 / ループ映像', '高'],
            ['YouTube解説動画', '8本', '撮影 + DaVinci Resolve編集', '中'],
            ['YouTube実践動画', '6本', '撮影 + 編集', '中'],
            ['リール動画', '8本', 'スマホ撮影 + CapCut編集', '中'],
            ['LINE登録特典PDF', '1冊（12P）', 'Canva / InDesign', '高'],
        ],
        col_widths=[42*mm, 32*mm, 50*mm, 29*mm]
    ))

    story.append(PageBreak())

    # ===== 6. FUNNEL =====
    story.append(Paragraph('6. 集客ファネル設計', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('6.1 ファネル全体像', s['JH2']))
    story.append(Paragraph(
        '認知 → 興味 → 信頼構築 → LINE登録 → 体験会参加 → 正会員/資格取得 のステップで顧客を育成する。',
        s['JBody']
    ))
    story.append(make_table(
        ['ステージ', 'チャネル', 'コンテンツ', '転換率目標'],
        [
            ['認知', 'X, Instagram, YouTube', '科学データ投稿、リール、BGM動画', '—'],
            ['興味', 'note無料記事, YouTube解説', '入門記事、メソッド解説動画', 'プロフ訪問率 5%'],
            ['信頼構築', 'Instagram カルーセル, note', '体験談、エビデンス、理事長メッセージ', 'フォロー率 10%'],
            ['LINE登録', 'CTA（全PF）', '無料PDF特典、ステップ配信', '登録率 3-5%'],
            ['体験会参加', 'LINE配信, イベント告知', '体験会案内、限定クーポン', '参加率 20%'],
            ['正会員化', '体験会後フォロー', '入会案内、メンバー特典紹介', '入会率 30%'],
            ['資格取得', '会員向けDM', '資格講座案内、卒業生の声', '申込率 10%'],
        ],
        col_widths=[25*mm, 40*mm, 50*mm, 38*mm]
    ))

    story.append(Paragraph('6.2 CTA（行動喚起）設計', s['JH2']))
    story.append(make_table(
        ['コンテンツタイプ', 'CTA', '誘導先'],
        [
            ['知識提供型（科学データ）', 'LINE登録で無料PDFプレゼント', 'LINE友だち追加'],
            ['ストーリー型（体験談）', '詳しくはnoteで', 'note無料記事'],
            ['データ型（研究結果）', '全データはマガジンで公開中', 'note有料マガジン'],
            ['実践型（やり方解説）', '動画で一緒にやってみよう', 'YouTube実践動画'],
            ['イベント型（告知）', '申込みはプロフのリンクから', 'イベント申込ページ'],
        ],
        col_widths=[42*mm, 52*mm, 59*mm]
    ))

    story.append(Paragraph('6.3 収益モデル', s['JH2']))
    story.append(make_table(
        ['収益源', '単価', '月間目標', '月額見込み'],
        [
            ['note有料記事', '500〜1,500円', '20件', '15,000円'],
            ['noteマガジン', '980円/月', '15人', '14,700円'],
            ['YouTube広告収益', '—', '—', '5,000円（Month 6以降）'],
            ['体験会参加費', '3,000円', '10名', '30,000円'],
            ['正会員入会金', '10,000円', '3名', '30,000円'],
            ['Harmonic Massage販売', '個別', '応相談', '別途'],
        ],
        col_widths=[38*mm, 30*mm, 30*mm, 55*mm]
    ))
    story.append(Paragraph('月間合計目標: 約95,000円〜150,000円', s['JCaption']))

    story.append(PageBreak())

    # ===== 7. TECH INFRA =====
    story.append(Paragraph('7. 技術インフラ（自動投稿システム）', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('7.1 システム概要', s['JH2']))
    story.append(Paragraph(
        'sns-auto-poster: TypeScript製の自動SNS投稿システム。YAMLファイルでコンテンツを管理し、'
        'GitHub ActionsまたはCloudflare Cron Triggerで定期実行。各プラットフォームのAPIに投稿する。',
        s['JBody']
    ))

    story.append(Paragraph('7.2 対応プラットフォーム・実装状況', s['JH2']))
    story.append(make_table(
        ['プラットフォーム', 'API', 'コード実装', 'API認証', '投稿データ'],
        [
            ['X (Twitter)', 'Twitter API v2', '完了', '未完了', '90本YAML済み'],
            ['LINE', 'Messaging API v9', '完了', '未完了', 'X投稿をLINEにも同時配信'],
            ['Instagram', 'Graph API v21.0', '完了', '未完了', '13本YAML済み'],
            ['YouTube', 'Data API v3', '未実装', '—', '台本のみ'],
        ],
        col_widths=[30*mm, 32*mm, 25*mm, 25*mm, 41*mm]
    ))

    story.append(Paragraph('7.3 API認証に必要な作業', s['JH2']))
    story.append(make_table(
        ['API', '必要な作業', '担当', '依存関係'],
        [
            ['X API', 'Developer Console復旧後にAPIキー生成', '康二郎', 'Console障害復旧待ち'],
            ['Instagram API', '①FBページに管理者追加 ②IG-FB接続 ③Dev App作成', '圭一郎→康二郎', '圭一郎の協力必須'],
            ['LINE API', '①管理画面ログイン情報確認 ②Messaging API有効化', '圭一郎→康二郎', '圭一郎の協力必須'],
        ],
        col_widths=[25*mm, 65*mm, 30*mm, 33*mm]
    ))

    story.append(Paragraph('7.4 投稿フロー', s['JH2']))
    for item in [
        '1. コンテンツをYAMLファイルで作成（content/posts/YYYY-MM/xxx.yaml）',
        '2. scheduled_atに投稿日時を指定',
        '3. GitHub Actions / Cloudflare Cronが定期的にスクリプトを実行',
        '4. 投稿時刻が来たYAMLを検出 → 各プラットフォームAPIに投稿',
        '5. 投稿結果をログに記録、ステータスを更新',
    ]:
        story.append(Paragraph(item, s['JBullet']))

    story.append(PageBreak())

    # ===== 8. MONTHLY ACTION PLAN =====
    story.append(Paragraph('8. 月別アクションプラン', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    months = [
        ('Month 1（2026年3月）: 基盤構築', [
            '圭一郎氏への依頼実施（FB管理者追加、IG-FB接続、LINE情報確認）',
            'X Developer Console復旧後、APIキー生成・.env設定',
            'Instagram Graph APIアクセストークン取得',
            'LINE Messaging API有効化・チャネル作成',
            'X自動投稿開始（毎日1本）',
            'Instagram投稿用画像制作開始（Canva）',
            'note初回記事公開（無料記事）',
            'LINE登録特典PDF制作',
            'YouTube BGM動画1本目制作・公開',
        ]),
        ('Month 2（2026年4月）: 全PF運用開始', [
            'Instagram定期投稿開始（週4回）',
            'YouTube週2本ペースで公開開始',
            'LINEステップ配信設定・運用開始',
            'note週1回投稿リズム確立',
            'GitHub Actions定期実行の安定運用確認',
            '4月分追加コンテンツ制作（X30本、IG16本、note4本）',
            'エンゲージメント分析・改善開始',
            'プロフィール・リンク最適化',
        ]),
        ('Month 3（2026年5月）: 成長加速', [
            'Instagram広告テスト（少額: 月5,000円〜）',
            '関連アカウントとのコラボ・相互紹介',
            '体験会「ここちよい音の日」のSNS集客強化',
            'note有料記事1本目公開',
            'YouTube再生リスト整備・SEO最適化',
            'ハッシュタグ戦略見直し',
            '5月分追加コンテンツ制作',
            'KPI中間レビュー・戦略修正',
        ]),
        ('Month 4（2026年6月）: 体験会誘導強化', [
            'Instagramリール動画量産（週2本目標）',
            'イベント告知の頻度アップ（各PFで週1回告知）',
            'note有料マガジン開始検討',
            'LINE配信のセグメント分け実施',
            'YouTube解説動画の制作ペースアップ',
            'Google Analytics / SNS分析ダッシュボード構築',
            '6月分コンテンツ制作',
        ]),
        ('Month 5（2026年7月）: コミュニティ構築', [
            'ファンコミュニティの仕組み構築（LINEオープンチャット等）',
            'UGC（ユーザー生成コンテンツ）促進キャンペーン',
            'メルマガ的なLINE配信の質向上',
            'YouTubeコミュニティ投稿活用',
            '体験会参加者のフォローアップ体制構築',
            '7月分コンテンツ制作',
            'スターライトヒーリング マラマハワイの告知（もし該当期間なら）',
        ]),
        ('Month 6（2026年8月）: 収益化確立', [
            'YouTube収益化条件達成・申請',
            'note有料コンテンツのラインナップ拡充',
            '資格認定講座の告知開始',
            'Instagram/X広告の本格運用',
            '6ヶ月間の総括レビュー',
            '次の6ヶ月の戦略策定',
            '海外展開（英語コンテンツ）の準備開始',
        ]),
    ]

    for title, items in months:
        story.append(Paragraph(title, s['JH2']))
        for item in items:
            story.append(Paragraph(f'□ {item}', s['JBullet']))

    story.append(PageBreak())

    # ===== 9. KPI =====
    story.append(Paragraph('9. KPI・目標設定', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('9.1 フォロワー・登録者目標', s['JH2']))
    story.append(make_table(
        ['プラットフォーム', 'Month 1', 'Month 2', 'Month 3', 'Month 4', 'Month 5', 'Month 6'],
        [
            ['X フォロワー', '50', '150', '300', '500', '700', '1,000'],
            ['IG フォロワー', '100', '300', '600', '1,000', '1,500', '2,000'],
            ['YT 登録者', '—', '100', '200', '350', '500', '700'],
            ['note フォロワー', '20', '50', '100', '150', '200', '300'],
            ['LINE 登録', '20', '50', '100', '150', '200', '300'],
        ],
        col_widths=[28*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm]
    ))

    story.append(Paragraph('9.2 エンゲージメント目標', s['JH2']))
    story.append(make_table(
        ['指標', 'Month 1-2', 'Month 3-4', 'Month 5-6'],
        [
            ['X インプレッション/投稿', '500', '1,000', '2,000'],
            ['IG リーチ/投稿', '200', '500', '1,000'],
            ['IG 保存率', '3%', '5%', '7%'],
            ['YT 平均再生時間', '—', '5分', '8分'],
            ['note スキ率', '5%', '8%', '10%'],
            ['LINE 開封率', '50%', '55%', '60%'],
        ],
        col_widths=[38*mm, 38*mm, 38*mm, 39*mm]
    ))

    story.append(Paragraph('9.3 収益目標', s['JH2']))
    story.append(make_table(
        ['収益源', 'Month 1-2', 'Month 3-4', 'Month 5-6'],
        [
            ['note有料記事', '0円', '15,000円/月', '30,000円/月'],
            ['YouTube広告', '0円', '0円', '5,000円/月'],
            ['体験会参加費', '0円', '15,000円/月', '30,000円/月'],
            ['正会員入会', '0円', '10,000円/月', '30,000円/月'],
            ['合計', '0円', '40,000円/月', '95,000円/月'],
        ],
        col_widths=[38*mm, 38*mm, 38*mm, 39*mm]
    ))

    story.append(PageBreak())

    # ===== 10. TASK LIST =====
    story.append(Paragraph('10. 必要タスク一覧', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('10.1 即時対応タスク（圭一郎氏への依頼）', s['JH2']))
    story.append(make_table(
        ['#', 'タスク', '詳細', '所要時間'],
        [
            ['1', 'FBページ管理者追加', 'harmonicscience FBページに康二郎を管理者として追加', '2分'],
            ['2', 'IG-FB接続', '@harmonicscience_jpとFBページを紐付け', '2分'],
            ['3', 'FB Developer登録', 'developers.facebook.comで電話認証（オプション）', '5分'],
            ['4', 'LINE管理画面情報', '@868hqnfwのログイン情報を共有', '1分'],
        ],
        col_widths=[8*mm, 38*mm, 82*mm, 25*mm]
    ))

    story.append(Paragraph('10.2 技術タスク（康二郎）', s['JH2']))
    story.append(make_table(
        ['#', 'タスク', '依存', '優先度'],
        [
            ['T1', 'X API キー生成・.env設定', 'Console復旧', '高'],
            ['T2', 'Instagram API アクセストークン取得', '圭一郎#1,#2完了', '高'],
            ['T3', 'LINE Messaging API チャネル作成', '圭一郎#4完了', '高'],
            ['T4', 'GitHub Actions ワークフロー設定', 'T1完了', '中'],
            ['T5', 'Instagram投稿用画像URL準備（公開URL必要）', '—', '中'],
            ['T6', 'Cloudflare Workers デプロイ設定', 'T1-T3完了', '低'],
            ['T7', '全プラットフォーム認証テスト実行', 'T1-T3完了', '高'],
            ['T8', 'テスト投稿（各PF）', 'T7完了', '高'],
        ],
        col_widths=[10*mm, 62*mm, 48*mm, 25*mm]
    ))

    story.append(Paragraph('10.3 コンテンツ制作タスク', s['JH2']))
    story.append(make_table(
        ['#', 'タスク', '対象', '優先度'],
        [
            ['C1', 'Instagramカルーセル画像制作', '20セット×5枚=100枚', '高'],
            ['C2', 'Instagram単画像制作', '15枚', '高'],
            ['C3', 'LINE登録特典PDF制作', '12ページ', '高'],
            ['C4', 'YouTube BGM動画制作', '6本（長尺音源+映像）', '高'],
            ['C5', 'YouTubeサムネイル制作', '24枚', '中'],
            ['C6', 'YouTube解説動画撮影・編集', '8本', '中'],
            ['C7', 'YouTube実践動画撮影・編集', '6本', '中'],
            ['C8', 'リール動画撮影・編集', '8本', '中'],
            ['C9', '4月以降の追加テキストコンテンツ制作', 'X30本/月 + IG16本/月 + note4本/月', '中'],
            ['C10', 'noteプロフィール・マガジン設定', '—', '高'],
        ],
        col_widths=[10*mm, 55*mm, 55*mm, 25*mm]
    ))

    story.append(Paragraph('10.4 運用タスク（継続）', s['JH2']))
    story.append(make_table(
        ['頻度', 'タスク', '担当'],
        [
            ['毎日', 'X投稿確認・エンゲージメント対応', '自動+手動'],
            ['週3-4回', 'Instagram投稿・ストーリーズ更新', '手動'],
            ['週2回', 'YouTube動画公開', '手動'],
            ['週1回', 'note記事公開', '手動'],
            ['週1回', 'LINE配信', '手動'],
            ['週1回', '週次KPIレビュー', '手動'],
            ['月1回', '月次レポート作成・戦略見直し', '手動'],
            ['月1回', '翌月コンテンツ一括制作', 'AI+手動'],
        ],
        col_widths=[25*mm, 85*mm, 43*mm]
    ))

    story.append(PageBreak())

    # ===== 11. RISKS =====
    story.append(Paragraph('11. リスクと対策', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(make_table(
        ['リスク', '影響度', '対策'],
        [
            ['API障害・仕様変更', '中', 'フォールバック手動投稿手順を準備、API変更ウォッチ'],
            ['「怪しい」ブランドイメージ', '高', '科学的エビデンス前面、医療関係者推薦、訴訟ゼロ実績を強調'],
            ['コンテンツ制作リソース不足', '高', 'AI活用で下書き効率化、Canvaテンプレート活用、外注検討'],
            ['フォロワー成長鈍化', '中', '広告テスト、コラボ、ハッシュタグ戦略見直し'],
            ['薬機法違反リスク', '高', '「治る」「治療」等の表現回避、体験談は個人の感想と明記'],
            ['圭一郎氏の協力遅延', '中', '依頼事項を一括化、代替手段（新規FB作成等）も検討'],
            ['YouTube収益化条件未達', '低', 'BGM長尺動画で再生時間を稼ぐ戦略、SEO最適化'],
        ],
        col_widths=[38*mm, 18*mm, 97*mm]
    ))

    story.append(Spacer(1, 5*mm))

    # ===== 12. BUDGET =====
    story.append(Paragraph('12. 予算概算', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(make_table(
        ['項目', '月額', '6ヶ月合計', '備考'],
        [
            ['Canva Pro', '1,500円', '9,000円', '画像制作ツール'],
            ['Instagram/X広告', '5,000円', '15,000円', 'Month 3以降'],
            ['X API (Free tier)', '0円', '0円', '月1,500ツイート制限'],
            ['Cloudflare Workers', '0円', '0円', 'Free tier十分'],
            ['ドメイン・ホスティング', '0円', '0円', '既存サイト利用'],
            ['LINE公式（フリープラン）', '0円', '0円', '月200通まで無料'],
            ['note（プレミアム）', '500円', '3,000円', '有料記事販売時'],
            ['動画編集ソフト', '0円', '0円', 'DaVinci Resolve無料版'],
            ['合計', '約7,000円/月', '約27,000円', '最小構成'],
        ],
        col_widths=[38*mm, 25*mm, 30*mm, 60*mm]
    ))
    story.append(Paragraph('※外注（画像制作、動画編集等）を行う場合は別途費用が発生', s['JCaption']))

    # ===== APPENDIX =====
    story.append(PageBreak())
    story.append(Paragraph('付録: 既存エビデンス資料（SNS活用可能）', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Paragraph(
        '以下の科学的データ・実験結果は、SNSコンテンツの信頼性を高めるソースとして活用可能。',
        s['JBody']
    ))

    story.append(make_table(
        ['年', '研究・データ', '主な結果', '活用先'],
        [
            ['2000', '日本健康科学学会 第16回学術大会', '自然音の健康効果に関する研究発表', 'note, X'],
            ['2008', '植物への自然音実験', '菊の花48日間実験: 自然音で生命力維持', 'IG, X'],
            ['2008', '循環器心身医学会', '体感音響のストレスケア効果', 'note'],
            ['2012', '骨密度研究（長田整形外科）', '70-80代女性で6ヶ月後骨密度上昇', 'IG, X, note'],
            ['2013', '温泉気候物理医学会', '成人女性10名中9名で副交感神経機能向上', 'IG, X'],
            ['2016', '自律神経機能実験', '被験者9名で副交感・交感神経両方の機能向上', 'X, IG'],
            ['2018', '筑波技術大学論文', '自然音の学術的分析', 'note'],
            ['2021', '水の構造変化実験', '60分自然音で水の構造変化を400倍画像で視覚化', 'IG, YT'],
            ['2024', 'スターライトヒーリング', '累計1,400名以上来場、ハワイ州観光局後援', 'IG, X'],
        ],
        col_widths=[15*mm, 45*mm, 55*mm, 28*mm]
    ))

    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=GRAY))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph('本プランは2026年3月6日時点の情報に基づく。状況に応じて適宜見直しを行う。', s['JFooter']))
    story.append(Paragraph('作成: Claude Code / 喜田康二郎', s['JFooter']))

    doc.build(story)
    print(f'PDF generated: {OUTPUT_PATH}')

if __name__ == '__main__':
    build_pdf()
