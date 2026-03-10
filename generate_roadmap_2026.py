#!/usr/bin/env python3
"""
サウンドヒーリング協会 2026年内ロードマップ PDF生成スクリプト
SNS投稿 → ファン獲得 → 収益化（セミナー、資格、note、YouTube等）
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

# Japanese fonts
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

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'ロードマップ_2026年内.pdf')


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
        textColor=PRIMARY, spaceBefore=8*mm, spaceAfter=4*mm
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

    # ===== COVER =====
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph('サウンドヒーリング協会', s['JTitle']))
    story.append(Paragraph('2026年 年間ロードマップ', s['JTitle']))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width='60%', thickness=2, color=PRIMARY))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('SNS発信 → ファン獲得 → 収益化', s['JSubtitle']))
    story.append(Paragraph('オンラインセミナー / 資格認定 / note / YouTube', s['JSubtitle']))
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph('NPO法人サウンドヒーリング協会 / 株式会社ジョイファンデーション', s['JSubtitle']))
    story.append(Paragraph('作成日: 2026年3月10日 | Version 1.0', s['JCaption']))
    story.append(PageBreak())

    # ===== TOC =====
    story.append(Paragraph('目次', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 3*mm))
    toc = [
        '1. エグゼクティブサマリー',
        '2. ファネル全体設計',
        '3. 四半期別ロードマップ（Q1: 3-4月 / Q2: 5-7月 / Q3: 8-10月 / Q4: 11-12月）',
        '4. 収益チャネル別戦略',
        '5. プラットフォーム別 年間KPI',
        '6. 月別マイルストーン一覧',
        '7. 収益シミュレーション',
        '8. 年間サマリー・次年度への展望',
    ]
    for item in toc:
        story.append(Paragraph(item, s['JBody']))
    story.append(PageBreak())

    # ===== 1. EXECUTIVE SUMMARY =====
    story.append(Paragraph('1. エグゼクティブサマリー', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Paragraph(
        '本ロードマップは、2026年3月〜12月の10ヶ月間で、サウンドヒーリング協会のSNS発信を起点に'
        'ファンを獲得し、複数の収益チャネルを確立するための実行計画である。',
        s['JBody']
    ))
    story.append(Paragraph('ビジョン', s['JH2']))
    story.append(Paragraph(
        '「自然音で心と体を整える」文化を広め、オンライン・オフライン双方で持続的な収益基盤を構築する。'
        '2026年末までに月間収益30万円、SNS総フォロワー10,000人を目指す。',
        s['JBody']
    ))
    story.append(Paragraph('4つの収益柱', s['JH2']))
    story.append(make_table(
        ['収益チャネル', '概要', '年末月額目標'],
        [
            ['オンラインセミナー', 'Zoom講座「音のウェルビーイング」\n月2回開催 × 4,000円', '80,000円/月'],
            ['資格認定講座', 'サウンドヒーリング・セラピスト認定\n半年コース × 150,000円', '75,000円/月'],
            ['note有料コンテンツ', '有料記事 + 月額マガジン\n500〜1,500円/本 + 980円/月', '50,000円/月'],
            ['YouTube広告収益', '長尺BGM動画中心\n収益化条件: 1,000人+4,000時間', '30,000円/月'],
        ],
        col_widths=[35*mm, 70*mm, 48*mm]
    ))
    story.append(Paragraph('※ 上記に加え、体験会参加費・正会員入会・機器販売等の副次収益あり', s['JCaption']))
    story.append(PageBreak())

    # ===== 2. FUNNEL =====
    story.append(Paragraph('2. ファネル全体設計', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Paragraph(
        'SNS各プラットフォームから段階的にファンを育成し、最終的に収益化アクションへ導く。',
        s['JBody']
    ))
    story.append(make_table(
        ['ステージ', 'チャネル', 'アクション', '転換率目標'],
        [
            ['認知', 'X / Instagram / YouTube', '科学データ投稿・リール・BGM動画', '—'],
            ['興味', 'note無料記事 / YouTube解説', '入門記事・メソッド解説動画', 'CTR 5%'],
            ['信頼構築', 'IG カルーセル / note連載', '体験談・エビデンス・理事長MSG', 'フォロー率 10%'],
            ['LINE登録', 'CTA（全PF共通）', '無料PDF特典・ステップ配信', '登録率 3-5%'],
            ['体験会参加', 'LINE / イベント告知', 'ここちよい音の日・ワークショップ', '参加率 20%'],
            ['セミナー受講', 'LINE / note / YouTube', 'オンライン講座（Zoom）4,000円', '受講率 15%'],
            ['正会員化', '体験会後フォロー', '入会案内・年会費10,000円', '入会率 30%'],
            ['資格取得', '会員向け案内', '認定講座150,000円 × 半年', '申込率 5%'],
        ],
        col_widths=[25*mm, 38*mm, 52*mm, 38*mm]
    ))

    story.append(Paragraph('ファネル数値モデル（年末目標）', s['JH2']))
    story.append(make_table(
        ['ステージ', '年末累計', '月間新規', '備考'],
        [
            ['SNS総フォロワー', '10,000人', '—', 'X+IG+YT+note+LINE合計'],
            ['LINE登録者', '500人', '50人/月', '全PFからの流入'],
            ['体験会参加者', '200人/年', '20人/月', 'ここちよい音の日 等'],
            ['セミナー受講者', '100人/年', '10人/月', 'Zoom講座 月2回'],
            ['正会員', '60人（新規）', '6人/月', '年会費10,000円'],
            ['資格受講者', '10人/年', '—', '半年コース 年2期'],
        ],
        col_widths=[35*mm, 35*mm, 30*mm, 53*mm]
    ))
    story.append(PageBreak())

    # ===== 3. QUARTERLY ROADMAP =====
    story.append(Paragraph('3. 四半期別ロードマップ', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    # Q1
    story.append(Paragraph('Q1: 基盤構築期（3月〜4月）', s['JH2']))
    story.append(Paragraph('テーマ: 全プラットフォーム立ち上げ・初動コンテンツ投入', s['JBody']))
    story.append(make_table(
        ['項目', '3月', '4月'],
        [
            ['X投稿', '毎日投稿開始（X-001〜）', '毎日投稿継続 + イベント4段告知'],
            ['Instagram', '初回9投稿でグリッド構築', '週4回投稿リズム確立'],
            ['YouTube', 'BGM動画3本（睡眠用3h等）', 'BGM3本 + 解説2本 + マラマハワイ'],
            ['note', '無料記事3本（入門シリーズ）', '無料3本 + 初の有料記事（500円）'],
            ['LINE', 'ステップ配信Day0-2設定', 'Day3-7設定完了・週1配信開始'],
            ['イベント', '—', 'ここちよい音の日(4/2-4)\nスターライトヒーリング(4/12)\nオンライン講座(4/14,23)'],
            ['収益目標', '0円', '25,000円'],
        ],
        col_widths=[28*mm, 62*mm, 63*mm]
    ))

    # Q2
    story.append(Paragraph('Q2: 成長加速期（5月〜7月）', s['JH2']))
    story.append(Paragraph('テーマ: エンゲージメント強化・有料コンテンツ本格化・広告テスト', s['JBody']))
    story.append(make_table(
        ['項目', '5月', '6月', '7月'],
        [
            ['X', '300フォロワー突破\nコラボ開始', '500フォロワー\nスペース開催', '700フォロワー\nUGC促進'],
            ['Instagram', '600フォロワー\n広告テスト開始', '1,000フォロワー\nリール量産', '1,500フォロワー\nインフルエンサー連携'],
            ['YouTube', '登録200人\nSEO最適化', '350人\n再生リスト整備', '500人\nコミュニティ投稿'],
            ['note', '有料マガジン開始\n月額980円', '有料記事月2本\n売上3万円/月', '連載企画開始\n売上4万円/月'],
            ['LINE', '100人突破\nセグメント配信', '150人\nリッチメニュー改善', '200人\nオープンチャット検討'],
            ['セミナー', '月2回定着\n受講者10人/月', '新テーマ追加\n企業向け開始', '夏期集中講座\n受講者15人/月'],
            ['収益目標', '50,000円', '80,000円', '120,000円'],
        ],
        col_widths=[22*mm, 38*mm, 38*mm, 38*mm]
    ))

    story.append(PageBreak())

    # Q3
    story.append(Paragraph('Q3: 収益化確立期（8月〜10月）', s['JH2']))
    story.append(Paragraph('テーマ: YouTube収益化・資格講座開講・コミュニティ深化', s['JBody']))
    story.append(make_table(
        ['項目', '8月', '9月', '10月'],
        [
            ['X', '1,000フォロワー\n固定ファン層形成', '1,200フォロワー\nニュースレター連携', '1,500フォロワー\n業界認知確立'],
            ['Instagram', '2,000フォロワー\nブランドコラボ', '2,500フォロワー\nショッピング連携', '3,000フォロワー\nIG Live定期開催'],
            ['YouTube', '700人\n収益化申請', '800人\n広告収益開始', '1,000人\n収益化条件達成'],
            ['note', '売上5万円/月\nマガジン50人', '連載完結記念\nセット販売', '売上5万円/月安定'],
            ['LINE', '300人\n自動化強化', '350人\nウェビナー連携', '400人\nVIP会員制度'],
            ['資格講座', '第1期募集開始\n5人目標', '第1期開講\n(〜2027年2月)', '第1期進行中\n第2期予告'],
            ['収益目標', '150,000円', '200,000円', '250,000円'],
        ],
        col_widths=[22*mm, 38*mm, 38*mm, 38*mm]
    ))

    # Q4
    story.append(Paragraph('Q4: 拡大・次年度準備期（11月〜12月）', s['JH2']))
    story.append(Paragraph('テーマ: 海外展開準備・2027年戦略策定・年間総括', s['JBody']))
    story.append(make_table(
        ['項目', '11月', '12月'],
        [
            ['X', '1,800フォロワー\n英語アカウント検討', '2,000フォロワー\n年間ベスト投稿'],
            ['Instagram', '3,500フォロワー\n海外ハッシュタグ', '4,000フォロワー\n年間総括リール'],
            ['YouTube', '1,200登録\n英語字幕追加', '1,500登録\n年末BGM特集'],
            ['note', '年間まとめ記事\n売上5万円安定', '2027年予告\nファンへの感謝'],
            ['LINE', '450人\n年末特別配信', '500人\n2027年予告'],
            ['資格講座', '第2期募集\n5人目標', '第2期開講準備\n第1期中間報告'],
            ['海外展開', '英語コンテンツ試作\nハワイ連携強化', '2027年海外戦略策定\n多言語対応計画'],
            ['収益目標', '280,000円', '300,000円'],
        ],
        col_widths=[28*mm, 62*mm, 63*mm]
    ))
    story.append(PageBreak())

    # ===== 4. REVENUE CHANNELS =====
    story.append(Paragraph('4. 収益チャネル別戦略', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('4.1 オンラインセミナー「音のウェルビーイング」', s['JH2']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['形式', 'Zoom（90〜120分）/ 月2回開催'],
            ['価格', '4,000円/回（正会員3,000円）'],
            ['テーマ', '「音の旅シリーズ」森の音/海の音/風の音/夜の音（4回ローテーション）'],
            ['集客経路', 'LINE配信 → 体験会参加者 → セミナー受講'],
            ['年末目標', '月20名受講 × 4,000円 = 80,000円/月'],
            ['成長戦略', 'Q1: 月2回(10名) → Q2: 月3回(15名) → Q3-4: 月4回(20名)'],
            ['将来展開', '企業向けストレスケア研修（1回50,000円〜）'],
        ],
        col_widths=[25*mm, 128*mm]
    ))

    story.append(Paragraph('4.2 資格認定講座', s['JH2']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['講座名', 'サウンドヒーリング・セラピスト認定講座'],
            ['形式', '半年コース（月2回 × 6ヶ月 = 全12回）'],
            ['価格', '150,000円（分割可: 30,000円×5回）'],
            ['内容', '自然音理論/体感音響実習/呼吸と声/カウンセリング/実技試験'],
            ['年間目標', '年2期 × 5名 = 10名 → 売上1,500,000円/年'],
            ['タイムライン', '8月: 第1期募集 → 9月: 開講 → 2月: 修了\n11月: 第2期募集 → 1月: 開講'],
            ['認定後', '協会認定セラピストとして活動可能・協会主催イベント講師資格'],
        ],
        col_widths=[25*mm, 128*mm]
    ))

    story.append(Paragraph('4.3 note有料コンテンツ', s['JH2']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['無料記事', '月2本 → SEO集客・信頼構築（入門/体験談/科学解説）'],
            ['有料記事', '月2本 × 500〜1,500円 → 実践メソッド/セルフケアプログラム'],
            ['月額マガジン', '「サウンドヒーリング実践ガイド」980円/月（5月開始）'],
            ['年末目標', '有料記事: 20件/月 × 平均800円 = 16,000円\nマガジン: 35人 × 980円 = 34,300円\n合計: 約50,000円/月'],
            ['成長戦略', 'Q1: 無料中心 → Q2: 有料開始 → Q3: マガジン安定 → Q4: セット販売'],
        ],
        col_widths=[25*mm, 128*mm]
    ))

    story.append(Paragraph('4.4 YouTube広告収益', s['JH2']))
    story.append(make_table(
        ['項目', '内容'],
        [
            ['収益化条件', '登録者1,000人 + 年間再生4,000時間'],
            ['達成見込み', '10月（Q3終盤）に条件達成予定'],
            ['コンテンツ戦略', 'BGM長尺（3h）: 再生時間稼ぎ主力\n解説動画（15分）: 登録者獲得\n実践ガイド（5分）: エンゲージメント'],
            ['年末月額目標', '30,000円/月（RPM 300円 × 10万再生想定）'],
            ['将来展開', 'メンバーシップ（月額490円）/ スーパーチャット / 限定ライブ'],
        ],
        col_widths=[25*mm, 128*mm]
    ))
    story.append(PageBreak())

    # ===== 5. PLATFORM KPI =====
    story.append(Paragraph('5. プラットフォーム別 年間KPI', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('5.1 フォロワー・登録者推移', s['JH2']))
    story.append(make_table(
        ['PF', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
        [
            ['X', '50', '150', '300', '500', '700', '1,000', '1,200', '1,500', '1,800', '2,000'],
            ['IG', '100', '300', '600', '1,000', '1,500', '2,000', '2,500', '3,000', '3,500', '4,000'],
            ['YT', '30', '100', '200', '350', '500', '700', '800', '1,000', '1,200', '1,500'],
            ['note', '20', '50', '100', '150', '200', '250', '300', '350', '400', '450'],
            ['LINE', '20', '50', '100', '150', '200', '300', '350', '400', '450', '500'],
        ],
        col_widths=[15*mm, 15*mm, 15*mm, 15*mm, 15*mm, 15*mm, 15*mm, 15*mm, 15*mm, 15*mm, 15*mm]
    ))

    story.append(Paragraph('5.2 エンゲージメント目標', s['JH2']))
    story.append(make_table(
        ['指標', 'Q1(3-4月)', 'Q2(5-7月)', 'Q3(8-10月)', 'Q4(11-12月)'],
        [
            ['X imp/投稿', '500', '1,500', '3,000', '5,000'],
            ['IG リーチ/投稿', '200', '800', '1,500', '2,500'],
            ['IG 保存率', '3%', '5%', '7%', '8%'],
            ['YT 平均再生', '—', '5分', '8分', '10分'],
            ['note スキ率', '5%', '8%', '10%', '12%'],
            ['LINE 開封率', '50%', '55%', '60%', '65%'],
        ],
        col_widths=[32*mm, 32*mm, 32*mm, 32*mm, 32*mm]
    ))

    story.append(Paragraph('5.3 投稿数（年間累計）', s['JH2']))
    story.append(make_table(
        ['PF', '月間投稿数', '年間累計（10ヶ月）', '制作済み', '追加制作必要'],
        [
            ['X', '30本/月', '300本', '90本', '210本'],
            ['Instagram', '16本/月', '160本', '48本', '112本'],
            ['YouTube', '8本/月', '80本', '0本（台本24本）', '80本'],
            ['note', '4本/月', '40本', '12本', '28本'],
            ['LINE', '4〜5通/月', '約45通', '7通', '約38通'],
        ],
        col_widths=[25*mm, 28*mm, 35*mm, 32*mm, 33*mm]
    ))
    story.append(PageBreak())

    # ===== 6. MONTHLY MILESTONES =====
    story.append(Paragraph('6. 月別マイルストーン一覧', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    milestones = [
        ('3月', '基盤構築', [
            'API認証完了（X / IG / LINE）',
            'X自動投稿開始',
            'Instagram初回9投稿でグリッド完成',
            'YouTube BGM動画3本公開',
            'note無料記事3本公開',
            'LINE ステップ配信設定（Day0-2）',
        ]),
        ('4月', '全PF運用開始', [
            '全プラットフォーム定期投稿リズム確立',
            'ここちよい音の日(4/2-4): SNS連動集客',
            'スターライトヒーリング(4/12): ダイジェスト動画',
            'オンライン講座初回(4/14, 4/23)',
            'note初の有料記事公開（500円）',
            'LINE ステップ配信全7通完成',
        ]),
        ('5月', '成長加速', [
            'Instagram広告テスト開始（月5,000円〜）',
            'note有料マガジン「実践ガイド」開始（月額980円）',
            'コラボ・相互紹介キャンペーン',
            'KPI中間レビュー・戦略修正',
        ]),
        ('6月', '体験会強化', [
            'リール動画量産（週2本体制）',
            'IG 1,000フォロワー突破',
            'noteマガジン購読者30人目標',
            'LINE セグメント配信開始',
            '企業向けストレスケア研修 試行',
        ]),
        ('7月', 'コミュニティ', [
            'LINEオープンチャット or Facebookグループ開設',
            'UGC促進キャンペーン',
            'YouTube 500登録突破',
            '夏期集中セミナー開催',
        ]),
        ('8月', '資格講座募集', [
            '資格認定講座 第1期生 募集開始（5名）',
            'YouTube 700登録 → 収益化申請準備',
            'IG 2,000フォロワー突破',
            'note月間売上5万円達成',
        ]),
        ('9月', '資格講座開講', [
            '第1期サウンドヒーリング・セラピスト認定講座 開講',
            'YouTube広告収益 開始',
            'IG ショッピング機能連携',
        ]),
        ('10月', '収益安定化', [
            'YouTube 1,000登録 収益化条件達成',
            'IG 3,000フォロワー',
            '月間収益25万円達成',
            'スターライトヒーリング 秋公演（予定）',
        ]),
        ('11月', '拡大準備', [
            '資格講座 第2期 募集開始',
            '英語コンテンツ試作',
            'ハワイ連携強化（現地イベント検討）',
            'X 1,800フォロワー',
        ]),
        ('12月', '年間総括', [
            '年間KPIレビュー・達成率確認',
            '2027年戦略策定',
            '月間収益30万円達成',
            'SNS総フォロワー10,000人（目標）',
            '海外展開計画確定',
        ]),
    ]

    for month, theme, items in milestones:
        story.append(Paragraph(f'{month}（{theme}）', s['JH3']))
        for item in items:
            story.append(Paragraph(f'□ {item}', s['JBullet']))

    story.append(PageBreak())

    # ===== 7. REVENUE SIMULATION =====
    story.append(Paragraph('7. 収益シミュレーション', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('7.1 月別収益推移', s['JH2']))
    story.append(make_table(
        ['月', 'セミナー', '資格講座', 'note', 'YouTube', '体験会他', '合計'],
        [
            ['3月', '0', '0', '0', '0', '0', '0'],
            ['4月', '16,000', '0', '2,000', '0', '7,000', '25,000'],
            ['5月', '32,000', '0', '8,000', '0', '10,000', '50,000'],
            ['6月', '48,000', '0', '15,000', '0', '17,000', '80,000'],
            ['7月', '60,000', '0', '25,000', '0', '35,000', '120,000'],
            ['8月', '60,000', '0', '35,000', '5,000', '50,000', '150,000'],
            ['9月', '64,000', '75,000', '40,000', '10,000', '11,000', '200,000'],
            ['10月', '72,000', '75,000', '45,000', '20,000', '38,000', '250,000'],
            ['11月', '76,000', '75,000', '48,000', '25,000', '56,000', '280,000'],
            ['12月', '80,000', '75,000', '50,000', '30,000', '65,000', '300,000'],
            ['年間計', '508,000', '300,000', '268,000', '90,000', '289,000', '1,455,000'],
        ],
        col_widths=[18*mm, 25*mm, 25*mm, 22*mm, 22*mm, 22*mm, 22*mm]
    ))
    story.append(Paragraph('※ 資格講座: 5名×150,000円=750,000円 を9月〜2月の6ヶ月で按分（月75,000円）', s['JCaption']))
    story.append(Paragraph('※ 体験会他: 体験会参加費+正会員入会+機器販売等の合算', s['JCaption']))

    story.append(Paragraph('7.2 投資対効果（ROI）', s['JH2']))
    story.append(make_table(
        ['項目', '年間費用', '備考'],
        [
            ['Canva Pro', '18,000円', '画像制作ツール（月1,500円）'],
            ['SNS広告費', '80,000円', 'Instagram/X広告（5月以降 月10,000円）'],
            ['note プレミアム', '6,000円', '有料記事販売機能（月500円）'],
            ['その他ツール', '10,000円', 'ドメイン・予備費'],
            ['費用合計', '114,000円', ''],
            ['', '', ''],
            ['年間売上見込', '1,455,000円', ''],
            ['年間利益', '1,341,000円', 'ROI: 1,176%'],
        ],
        col_widths=[35*mm, 35*mm, 83*mm]
    ))
    story.append(Paragraph('※ 人件費（自身の労働時間）は含まず。外注する場合は別途。', s['JCaption']))

    story.append(PageBreak())

    # ===== 8. ANNUAL SUMMARY =====
    story.append(Paragraph('8. 年間サマリー・次年度への展望', s['JH1']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))

    story.append(Paragraph('8.1 2026年の達成目標まとめ', s['JH2']))
    story.append(make_table(
        ['カテゴリ', '指標', '年末目標'],
        [
            ['SNS', '総フォロワー数', '10,000人（X:2,000 / IG:4,000 / YT:1,500 / note:450 / LINE:500等）'],
            ['収益', '月間売上', '300,000円/月（12月時点）'],
            ['収益', '年間売上累計', '1,455,000円'],
            ['セミナー', '年間受講者', '100名'],
            ['資格', '認定セラピスト', '5名（第1期）'],
            ['イベント', '体験会参加者', '200名/年'],
            ['会員', '新規正会員', '60名'],
            ['YouTube', '収益化', '10月に条件達成・収益化開始'],
        ],
        col_widths=[25*mm, 35*mm, 93*mm]
    ))

    story.append(Paragraph('8.2 2027年への展望', s['JH2']))
    for item in [
        '海外展開: 英語コンテンツ本格化、ハワイ現地イベント定期開催',
        '資格講座拡大: 年4期開講（各5名 = 年20名）、上級コース新設',
        'オンラインサロン: 月額制コミュニティ（月2,980円 × 100名 = 298,000円/月）',
        'YouTube メンバーシップ: 限定動画・ライブ配信（月490円）',
        '法人向け事業拡大: 企業ストレスケア研修（1社50,000円〜/回）',
        '書籍出版: 理事長著書のKindle/紙出版',
        '音源サブスクリプション: 月額課金型自然音配信サービス',
        '年間売上目標: 500万円/年（月42万円）',
    ]:
        story.append(Paragraph(f'・{item}', s['JBullet']))

    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=GRAY))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        '本ロードマップは2026年3月10日時点の情報に基づく。毎月のKPIレビューにより適宜見直しを行う。',
        s['JFooter']
    ))
    story.append(Paragraph('作成: Claude Code / 喜田康二郎', s['JFooter']))

    doc.build(story)
    print(f'PDF generated: {OUTPUT_PATH}')


if __name__ == '__main__':
    build_pdf()
