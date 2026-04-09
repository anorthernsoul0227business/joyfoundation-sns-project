#!/usr/bin/env python3
"""
SNS投稿スケジュール → Google Calendar ICSファイル生成
3月・4月の全投稿予定 + イベント情報をカレンダーにインポート可能な形式で出力
"""

import os
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.dirname(__file__)

def ics_escape(text):
    """ICS形式のテキストエスケープ"""
    return text.replace('\\', '\\\\').replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')

def make_event(uid, dtstart, dtend, summary, description='', color_id='', location=''):
    """単一イベントのICS文字列生成"""
    lines = [
        'BEGIN:VEVENT',
        f'UID:{uid}@shkyoukai.calendar',
        f'DTSTART;TZID=Asia/Tokyo:{dtstart}',
        f'DTEND;TZID=Asia/Tokyo:{dtend}',
        f'SUMMARY:{ics_escape(summary)}',
    ]
    if description:
        lines.append(f'DESCRIPTION:{ics_escape(description)}')
    if location:
        lines.append(f'LOCATION:{ics_escape(location)}')
    # Google Calendar color (via X-GOOGLE-CALENDAR-CONTENT-COLOR doesn't work in import)
    # Use categories instead
    if color_id:
        lines.append(f'CATEGORIES:{color_id}')
    lines.append('END:VEVENT')
    return '\n'.join(lines)

def make_allday_event(uid, date_str, summary, description='', location=''):
    """終日イベント"""
    lines = [
        'BEGIN:VEVENT',
        f'UID:{uid}@shkyoukai.calendar',
        f'DTSTART;VALUE=DATE:{date_str}',
        f'DTEND;VALUE=DATE:{date_str}',
        f'SUMMARY:{ics_escape(summary)}',
    ]
    if description:
        lines.append(f'DESCRIPTION:{ics_escape(description)}')
    if location:
        lines.append(f'LOCATION:{ics_escape(location)}')
    lines.append('END:VEVENT')
    return '\n'.join(lines)

def generate_ics():
    events = []

    # ==========================================
    # リアルイベント（時間指定あり）
    # ==========================================

    # ここちよい音の日 4/2-4
    for day in ['02', '03', '04']:
        events.append(make_event(
            f'event-kokochiyo-04{day}',
            f'20260402T130000' if day == '02' else f'202604{day}T130000',
            f'20260402T160000' if day == '02' else f'202604{day}T160000',
            '🌿 ここちよい音の日',
            '太陽食品世田谷店 & SH協会コラボ\\n体験500円\\n13:00〜16:00\\n約10分のサウンドヒーリング体験',
            location='太陽食品世田谷店（東急大井町線 尾山台駅 徒歩3分）'
        ))

    # スターライトヒーリング マラマハワイ 4/12
    events.append(make_event(
        'event-malama-0412',
        '20260412T133000',
        '20260412T142000',
        '⭐ スターライトヒーリング マラマハワイ追加公演',
        '大人620円 / 小人310円\\nハワイの星空と自然音の癒し体験\\n後援: ハワイ州観光局',
        location='さいたま市宇宙劇場（JACK大宮3階）'
    ))

    # オンライン講座 第1回 4/14
    events.append(make_event(
        'event-online-0414',
        '20260414T100000',
        '20260414T120000',
        '🎓 オンライン講座「音のウェルビーイング」第1回',
        'Zoom開催\\n参加費: 4,000円\\n「音の旅シリーズ」',
        location='Zoom'
    ))

    # オンライン講座 第2回 4/23
    events.append(make_event(
        'event-online-0423',
        '20260423T100000',
        '20260423T120000',
        '🎓 オンライン講座「音のウェルビーイング」第2回',
        'Zoom開催\\n参加費: 4,000円',
        location='Zoom'
    ))

    # ==========================================
    # X（Twitter）投稿 — 毎日9:00
    # ==========================================
    x_posts_march = [
        ('0310', 'X-001', '体感音響実験で心拍数低下・副交感神経機能の亢進を確認', '科学データ'),
        ('0311', 'X-058', 'ここちよい音の日（毎月開催の無料体験会）', 'イベント告知'),
        ('0312', 'X-037', '「音は心の糧である」── 喜田圭一郎理事長', '名言・理念'),
        ('0313', 'X-073', '【note更新】NOTE-001連動シェア', '記事シェア'),
        ('0314', 'X-002', '自律神経の2種類（交感神経=アクセル、副交感神経=ブレーキ）', '科学データ'),
        ('0315', 'X-056', 'スターライトヒーリング マラマハワイ紹介', 'イベント告知'),
        ('0316', 'X-038', '「心と体に自然のリズムを取り戻す」協会コンセプト', '名言・理念'),
        ('0317', 'X-003', '福祉ワーカー13名・週2回15分の自然音で睡眠改善', '科学データ'),
        ('0318', 'X-057', 'Harmonic Day（正会員限定オンラインイベント）', 'イベント告知'),
        ('0319', 'X-039', 'ゲイナー博士「音は古代から治癒力促進に使用されてきた」', '名言・理念'),
        ('0320', 'X-074', '【ブログ更新】自然音が自律神経に与える影響', '記事シェア'),
        ('0321', 'X-004', '東京大学大学院の研究「音刺激で精神的ストレス低減」', '科学データ'),
        ('0322', 'X-059', 'Healing Garden 体験セッション（自由が丘）', 'イベント告知'),
        ('0323', 'X-040', '「未病」の考え方─病気にならない体をつくる', '名言・理念'),
        ('0324', 'X-005', '足底への音響刺激で自律神経機能が向上', '科学データ'),
        ('0325', 'X-060', 'オンラインワークショップ（初心者向け入門講座）', 'イベント告知'),
        ('0326', 'X-041', '「自然界にある音はすべて意味がある」', '名言・理念'),
        ('0327', 'X-075', '【YouTube公開】YT-BGM-001連動シェア', '記事シェア'),
        ('0328', 'X-006', '温泉気候医学会報告：9例中9例で心拍数低下', '科学データ'),
        ('0329', 'X-067', '会員募集中（正会員のメリット紹介）', 'イベント告知'),
        ('0330', 'X-042', '日野原重明先生と喜田理事長の交流「音楽は人を癒す」', '名言・理念'),
        ('0331', 'X-007', '人体の約70%は水分─体感音響の科学的根拠', '科学データ'),
    ]

    x_posts_april = [
        ('0401', 'X-055', '【明日から開催】ここちよい音の日 4/2-4 太陽食品世田谷店コラボ', 'イベント告知'),
        ('0402', 'X-055', '【本日開催中】ここちよい音の日 太陽食品世田谷店 13:00〜16:00', 'イベント告知'),
        ('0403', 'X-076', '【協会誌より】サウンドヒーリングの最新情報', '記事シェア'),
        ('0404', 'X-008', '低い音は体に共鳴し弛緩、高い音は意識を覚醒', '科学データ'),
        ('0405', 'X-055', '【1週間後】マラマハワイ追加公演 4/12', 'イベント告知'),
        ('0406', 'X-043', '「Harmonic Revolution」─ 調和の革命', '名言・理念'),
        ('0407', 'X-070', '【1週間後】オンライン講座 4/14 Zoom 4,000円', 'イベント告知'),
        ('0408', 'X-009', 'うつ病患者62名への施術で気分改善', '科学データ'),
        ('0409', 'X-061', '【3日後】マラマハワイ追加公演 4/12 大人620円', 'イベント告知'),
        ('0410', 'X-077', '【おすすめ記事】サウンドヒーリング入門ガイド', '記事シェア'),
        ('0411', 'X-062', '【明日】マラマハワイ & 【3日後】オンライン講座', 'イベント告知'),
        ('0412', 'X-055', '【本日開催】マラマハワイ さいたま市宇宙劇場 13:30〜', 'イベント告知'),
        ('0413', 'X-062', '【明日開催】オンライン講座 第1回 Zoom 10:00〜12:00', 'イベント告知'),
        ('0414', 'X-070', '【本日開催】オンライン講座 第1回 10:00〜', 'イベント告知'),
        ('0415', 'X-010', '副交感神経が優位になると─筋肉緩和・腸管安定・呼吸深化', '科学データ'),
        ('0416', 'X-070', '【1週間後】オンライン講座 第2回 4/23 Zoom', 'イベント告知'),
        ('0417', 'X-078', '【研究紹介】note記事で科学的根拠を詳しく解説', '記事シェア'),
        ('0418', 'X-011', '5種類のリラクセーション法比較─状態不安が有意に減少', '科学データ'),
        ('0419', 'X-044', 'ピタゴラス「宇宙は音楽である」─2500年前からの知恵', '名言・理念'),
        ('0420', 'X-061', '【3日後】オンライン講座 第2回 4/23 Zoom', 'イベント告知'),
        ('0421', 'X-012', '自律神経バランスの乱れチェック─1日15分の自然音から', '科学データ'),
        ('0422', 'X-062', '【明日開催】オンライン講座 第2回 Zoom 10:00〜12:00', 'イベント告知'),
        ('0423', 'X-070', '【本日開催】オンライン講座 第2回 10:00〜', 'イベント告知'),
        ('0424', 'X-079', '【体験談紹介】会員のサウンドヒーリング体験記', '記事シェア'),
        ('0425', 'X-013', '1/fゆらぎとは─自然音が心地よい科学的理由', '科学データ'),
        ('0426', 'X-045', '「自分を信じる時代」─自分軸を持つことの大切さ', '名言・理念'),
        ('0427', 'X-046', '「体で聴く」という体験─体感音響', '名言・理念'),
        ('0428', 'X-014', '人工音に不快・自然音に快適─これは本能', '科学データ'),
        ('0429', 'X-047', '「音はこれから更に社会に貢献していくだろう」', '名言・理念'),
        ('0430', 'X-080', '【実践ガイド】自宅でできる自然音の聴き方動画', '記事シェア'),
    ]

    for posts, month in [(x_posts_march, '03'), (x_posts_april, '04')]:
        for date_suffix, code, title, cat in posts:
            events.append(make_event(
                f'x-{code}-2026{date_suffix}',
                f'2026{date_suffix}T090000',
                f'2026{date_suffix}T091500',
                f'[X] {code} {title}',
                f'カテゴリ: {cat}\\nアカウント: @SFH_Science',
                color_id='X投稿'
            ))

    # ==========================================
    # Instagram投稿 — 12:00
    # ==========================================
    ig_march = [
        ('0310', 'IG-C-001', 'カルーセル', '自律神経と自然音の関係'),
        ('0312', 'IG-S-001', '単画像', '音は環境要因（名言画像）'),
        ('0314', 'IG-C-002', 'カルーセル', 'オキシトシンと自然音'),
        ('0315', 'IG-R-001', 'リール', '1分でわかる自然音の効果'),
        ('0317', 'IG-C-003', 'カルーセル', '1/fゆらぎの秘密'),
        ('0319', 'IG-S-002', '単画像', '体は70%水分（科学図解）'),
        ('0321', 'IG-C-004', 'カルーセル', '睡眠の質を上げる自然音'),
        ('0322', 'IG-E-001', 'イベント告知', 'オンラインHarmonic Day告知'),
        ('0324', 'IG-C-005', 'カルーセル', '体感音響とは'),
        ('0326', 'IG-S-003', '単画像', '低い音は弛緩、高い音は覚醒'),
        ('0328', 'IG-C-006', 'カルーセル', '呼吸と声のヒーリング'),
        ('0329', 'IG-R-002', 'リール', '寝つきが悪い人へ（睡眠改善法）'),
        ('0331', 'IG-C-007', 'カルーセル', '水への自然音実験'),
    ]

    ig_april = [
        ('0401', 'IG-E-002', 'イベント告知', '【明日から】ここちよい音の日 太陽食品世田谷店コラボ'),
        ('0402', 'IG-S-004', '単画像', '心と体に自然のリズムを（名言画像）'),
        ('0404', 'IG-C-008', 'カルーセル', '植物と自然音の実験（48日間）'),
        ('0405', 'IG-E-003', 'イベント告知', 'マラマハワイ追加公演 4/12告知'),
        ('0407', 'IG-C-009', 'カルーセル', '骨密度と自然音（70代・80代女性の実例）'),
        ('0409', 'IG-S-005', '単画像', '自分軸を持つことの大切さ'),
        ('0411', 'IG-R-003', 'リール', '肩こりと自律神経（体感音響紹介）'),
        ('0412', 'IG-E-003', 'イベント告知', '【本日開催】マラマハワイ追加公演 レポート予告'),
        ('0414', 'IG-C-010', 'カルーセル', '現代人と人工音（音のストレス）'),
        ('0416', 'IG-S-006', '単画像', '病院に頼らない生き方'),
        ('0418', 'IG-C-011', 'カルーセル', '朝・昼・夜の自然音活用法'),
        ('0419', 'IG-R-004', 'リール', '声で自分を癒す（呼吸と声の実践）'),
        ('0421', 'IG-C-012', 'カルーセル', '更年期と自律神経'),
        ('0423', 'IG-S-007', '単画像', '呼吸を整えると心が整う'),
        ('0425', 'IG-C-013', 'カルーセル', '在宅ワークの音環境（集中力UP）'),
        ('0426', 'IG-E-004', 'イベント告知', 'Harmonic Scienceフォーラム告知'),
        ('0428', 'IG-C-014', 'カルーセル', '子育て後の自分時間（セルフケア習慣）'),
        ('0430', 'IG-S-008', '単画像', '朝5分の自然音習慣'),
    ]

    for posts in [ig_march, ig_april]:
        for date_suffix, code, fmt, title in posts:
            events.append(make_event(
                f'ig-{code}-2026{date_suffix}',
                f'2026{date_suffix}T120000',
                f'2026{date_suffix}T121500',
                f'[IG] {code} [{fmt}] {title}',
                f'形式: {fmt}\\nアカウント: @harmonicscience_jp',
                color_id='Instagram投稿'
            ))

    # ==========================================
    # YouTube — 15:00
    # ==========================================
    yt_march = [
        ('0311', 'YT-BGM-001', '長尺BGM', '【睡眠用BGM】森の自然音 3時間'),
        ('0314', 'YT-EDU-001', '解説・教育', 'なぜ自然音は体に良いのか？科学的に解説'),
        ('0318', 'YT-BGM-002', '長尺BGM', '【作業用BGM】小川のせせらぎ 2時間'),
        ('0321', 'YT-PRC-001', '実践ガイド', '【5分実践】自律神経を整える呼吸法'),
        ('0325', 'YT-BGM-003', '長尺BGM', '【リラックスBGM】波の音 3時間'),
        ('0328', 'YT-EDU-002', '解説・教育', '1/fゆらぎとは？心地よさの科学'),
    ]

    yt_april = [
        ('0401', 'YT-BGM-004', '長尺BGM', '【睡眠用BGM】雨の音 2時間'),
        ('0404', 'YT-EDU-003', '解説・教育', '自律神経を整える3つの方法'),
        ('0408', 'YT-PRC-002', '実践ガイド', '朝の自然音ルーティン 10分'),
        ('0411', 'YT-EVT-001', 'イベント記録', 'マラマハワイ ダイジェスト'),
        ('0415', 'YT-BGM-005', '長尺BGM', '【朝の目覚め】鳥のさえずり 1時間'),
        ('0418', 'YT-EDU-004', '解説・教育', '睡眠の質を上げる自然音の使い方'),
        ('0422', 'YT-PRC-003', '実践ガイド', '寝る前の自然音ルーティン 15分'),
        ('0425', 'YT-EDU-005', '解説・教育', '体感音響とは？耳だけでなく体で聴く'),
    ]

    for posts in [yt_march, yt_april]:
        for date_suffix, code, cat, title in posts:
            events.append(make_event(
                f'yt-{code}-2026{date_suffix}',
                f'2026{date_suffix}T150000',
                f'2026{date_suffix}T151500',
                f'[YT] {code} {title}',
                f'カテゴリ: {cat}\\nチャンネル: @harmonicscience2651',
                color_id='YouTube投稿'
            ))

    # ==========================================
    # note — 10:00
    # ==========================================
    note_march = [
        ('0313', 'NOTE-001', '無料', '自然音入門 ─ なぜ今、自然音が注目されているのか'),
        ('0320', 'NOTE-002', '無料', '自律神経を整える自然音の聴き方'),
        ('0327', 'NOTE-003', '無料', '体感音響とは ─ 耳だけでなく体で聴く'),
    ]

    note_april = [
        ('0403', 'NOTE-004', '無料', '呼吸と声のヒーリング ─ 自分の声で自分を癒す'),
        ('0410', 'NOTE-005', '無料', '喜田圭一郎理事長が語る「Harmonic Revolution」'),
        ('0417', 'NOTE-P-001', '有料(500円)', '【実践講座1】自然音で眠る ─ 睡眠改善完全ガイド'),
        ('0424', 'NOTE-006', '無料', 'サウンドヒーリング協会の20年'),
    ]

    for posts in [note_march, note_april]:
        for date_suffix, code, price, title in posts:
            events.append(make_event(
                f'note-{code}-2026{date_suffix}',
                f'2026{date_suffix}T100000',
                f'2026{date_suffix}T101500',
                f'[note] {code} [{price}] {title}',
                f'種類: {price}',
                color_id='note投稿'
            ))

    # ==========================================
    # LINE — 18:00
    # ==========================================
    line_march = [
        ('0312', 'Day0', 'あいさつ＋特典PDF「自然音入門ガイド」プレゼント'),
        ('0319', 'Day1', '自己紹介＋協会紹介（3つのメソッド）'),
        ('0326', 'Day2', '自然音の科学（研究データ3つ紹介）'),
    ]

    line_april = [
        ('0402', 'Day3', '体感音響の紹介（3メソッド紹介）'),
        ('0409', 'Day4', '体験者の声（50代・60代・40代女性の声）'),
        ('0416', 'Day5', '体験会のご案内（ここちよい音の日・Harmonic Day）'),
        ('0423', 'Day7', '正会員のご案内（年会費・特典紹介）'),
    ]

    for posts in [line_march, line_april]:
        for date_suffix, step, content in posts:
            events.append(make_event(
                f'line-{step}-2026{date_suffix}',
                f'2026{date_suffix}T180000',
                f'2026{date_suffix}T181500',
                f'[LINE] {step}: {content}',
                f'アカウント: @868hqnfw',
                color_id='LINE配信'
            ))

    # ==========================================
    # ICSファイル生成
    # ==========================================
    ics_content = '\n'.join([
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//SH協会//SNSスケジュール//JP',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:SH協会 SNSスケジュール',
        'X-WR-TIMEZONE:Asia/Tokyo',
        'BEGIN:VTIMEZONE',
        'TZID:Asia/Tokyo',
        'BEGIN:STANDARD',
        'DTSTART:19700101T000000',
        'TZOFFSETFROM:+0900',
        'TZOFFSETTO:+0900',
        'END:STANDARD',
        'END:VTIMEZONE',
    ])

    for event in events:
        ics_content += '\n' + event

    ics_content += '\nEND:VCALENDAR\n'

    # 全件ICS
    output_path = os.path.join(OUTPUT_DIR, 'SNSスケジュール_3月4月.ics')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ics_content)
    print(f'Generated: {output_path} ({len(events)} events)')

    # イベントのみICS（リアルイベント4件）
    event_only = [e for e in events if 'event-' in e]
    ics_events = '\n'.join([
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//SH協会//イベント//JP',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:SH協会 イベント',
        'X-WR-TIMEZONE:Asia/Tokyo',
        'BEGIN:VTIMEZONE',
        'TZID:Asia/Tokyo',
        'BEGIN:STANDARD',
        'DTSTART:19700101T000000',
        'TZOFFSETFROM:+0900',
        'TZOFFSETTO:+0900',
        'END:STANDARD',
        'END:VTIMEZONE',
    ])
    for event in event_only:
        ics_events += '\n' + event
    ics_events += '\nEND:VCALENDAR\n'

    output_events = os.path.join(OUTPUT_DIR, 'イベント_4月.ics')
    with open(output_events, 'w', encoding='utf-8') as f:
        f.write(ics_events)
    print(f'Generated: {output_events} ({len(event_only)} events)')


if __name__ == '__main__':
    generate_ics()
