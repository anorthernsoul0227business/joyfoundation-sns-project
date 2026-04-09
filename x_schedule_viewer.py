#!/usr/bin/env python3
"""X投稿スケジュール管理 - HTML表示版"""

import json
import os

SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), 'x_schedule.json')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'X投稿スケジュール管理.html')

def load_schedule():
    with open(SCHEDULE_FILE, 'r') as f:
        return json.load(f)

def generate_html():
    schedule = load_schedule()

    status_info = {
        'draft': ('📝 下書き', '#f5f5f5', '#666'),
        'scheduled': ('🕐 予約済', '#e3f2fd', '#1565c0'),
        'posted': ('✅ 投稿済', '#e8f5e9', '#2e7d32'),
        'skipped': ('⏭️ スキップ', '#fff3e0', '#ef6c00'),
    }

    counts = {}
    for item in schedule:
        counts[item['status']] = counts.get(item['status'], 0) + 1

    summary_parts = []
    for status, count in counts.items():
        label, bg, color = status_info[status]
        summary_parts.append(f'<span style="background:{bg};color:{color};padding:4px 12px;border-radius:16px;font-size:14px;font-weight:bold">{label} {count}本</span>')

    rows = ''
    for item in schedule:
        label, bg, color = status_info[item['status']]
        sched = item['scheduled_at'] or '—'
        posted = item['posted_at'] or '—'

        # Escape HTML in text
        text_escaped = item['text'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # Highlight hashtags
        import re
        text_escaped = re.sub(r'(#\S+)', r'<span style="color:#1da1f2">\1</span>', text_escaped)

        char_warning = ' style="color:#e53935;font-weight:bold"' if item['chars'] > 280 else ''

        rows += f'''
    <div class="card" id="post-{item['id']}">
      <div class="card-header">
        <div class="card-id">{item['id']}</div>
        <div class="card-meta">
          <div class="card-title">{item['title']}</div>
          <div class="card-stats">
            <span class="badge" style="background:{bg};color:{color}">{label}</span>
            <span{char_warning}>{item['chars']}文字</span>
            {f'<span>予約: {sched}</span>' if item['scheduled_at'] else ''}
          </div>
        </div>
      </div>
      <div class="card-body"><pre>{text_escaped}</pre></div>
    </div>'''

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X投稿スケジュール管理 - @SFH_Science</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',sans-serif; background:#f0f2f5; color:#1a1a1a; }}
.container {{ max-width:900px; margin:0 auto; padding:20px; }}
h1 {{ text-align:center; font-size:22px; margin:20px 0 8px; }}
.subtitle {{ text-align:center; color:#536471; font-size:14px; margin-bottom:20px; }}
.summary {{ display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-bottom:24px; padding:16px; background:#fff; border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
.card {{ background:#fff; border-radius:12px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.08); overflow:hidden; }}
.card-header {{ display:flex; align-items:flex-start; padding:16px; gap:12px; cursor:pointer; }}
.card-header:hover {{ background:#f8f9fa; }}
.card-id {{ width:36px; height:36px; border-radius:50%; background:#1da1f2; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:14px; flex-shrink:0; }}
.card-meta {{ flex:1; }}
.card-title {{ font-weight:bold; font-size:15px; margin-bottom:6px; }}
.card-stats {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
.card-stats span {{ font-size:13px; color:#536471; }}
.badge {{ padding:2px 10px; border-radius:12px; font-size:12px !important; font-weight:bold; }}
.card-body {{ display:none; padding:0 16px 16px 64px; }}
.card-body.open {{ display:block; }}
.card-body pre {{ white-space:pre-wrap; word-wrap:break-word; font-family:inherit; font-size:15px; line-height:1.7; background:#f8f9fa; padding:16px; border-radius:8px; border:1px solid #e8e8e8; }}
.filter-bar {{ display:flex; gap:8px; justify-content:center; margin-bottom:20px; flex-wrap:wrap; }}
.filter-btn {{ padding:6px 16px; border-radius:20px; border:1px solid #ddd; background:#fff; cursor:pointer; font-size:13px; }}
.filter-btn:hover {{ background:#f0f0f0; }}
.filter-btn.active {{ background:#1da1f2; color:#fff; border-color:#1da1f2; }}
.cmd {{ background:#1a1a2e; color:#e0e0e0; padding:16px; border-radius:8px; font-family:monospace; font-size:13px; line-height:1.8; margin-top:24px; white-space:pre-wrap; }}
.cmd strong {{ color:#4fc3f7; }}
.cmd .comment {{ color:#6a9955; }}
</style>
</head>
<body>
<div class="container">
<h1>X投稿スケジュール管理</h1>
<p class="subtitle">@SFH_Science ・ 全{len(schedule)}本</p>

<div class="summary">{" ".join(summary_parts)}</div>

<div class="filter-bar">
  <button class="filter-btn active" onclick="filterPosts('all')">すべて</button>
  <button class="filter-btn" onclick="filterPosts('draft')">📝 下書き</button>
  <button class="filter-btn" onclick="filterPosts('scheduled')">🕐 予約済</button>
  <button class="filter-btn" onclick="filterPosts('posted')">✅ 投稿済</button>
</div>

{rows}

<div class="cmd">
<strong>コマンドリファレンス</strong>
<span class="comment"># 一覧表示</span>
python3 x_scheduler.py list

<span class="comment"># 投稿の詳細確認</span>
python3 x_scheduler.py show 5

<span class="comment"># 個別に予約</span>
python3 x_scheduler.py schedule 5 "2026-03-25 09:00"

<span class="comment"># 一括予約（開始日から1日2本ずつ）</span>
python3 x_scheduler.py bulk "2026-03-25"

<span class="comment"># 予約時刻の投稿を実行</span>
python3 x_scheduler.py run

<span class="comment"># 即時投稿（確認プロンプトあり）</span>
python3 x_scheduler.py post 5

<span class="comment"># テキスト編集</span>
python3 x_scheduler.py edit 5

<span class="comment"># このHTMLを再生成</span>
python3 x_schedule_viewer.py
</div>

</div>

<script>
document.querySelectorAll('.card-header').forEach(header => {{
  header.addEventListener('click', () => {{
    const body = header.nextElementSibling;
    body.classList.toggle('open');
  }});
}});

function filterPosts(status) {{
  document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.card').forEach(card => {{
    if (status === 'all') {{
      card.style.display = '';
    }} else {{
      const badge = card.querySelector('.badge');
      const map = {{'draft':'下書き','scheduled':'予約済','posted':'投稿済','skipped':'スキップ'}};
      card.style.display = badge.textContent.includes(map[status]) ? '' : 'none';
    }}
  }});
}}
</script>
</body>
</html>'''

    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)
    print(f"✓ HTML生成完了 → {OUTPUT_FILE}")

if __name__ == '__main__':
    generate_html()
