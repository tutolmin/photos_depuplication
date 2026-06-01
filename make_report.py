#!/usr/bin/env python3
"""
Генератор HTML-отчёта по дубликатам из JSON-вывода команды `dups`.

Использование:
    python registry.py dups | python make_report.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path


CSS = r"""
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#f5f5f5;padding:24px;color:#333}
h1{margin-bottom:4px;font-size:22px}
.summary{color:#666;margin-bottom:24px;font-size:13px}
.group{background:#fff;border-radius:8px;padding:20px;
       margin-bottom:28px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.group-header{margin-bottom:16px;padding-bottom:12px;
              border-bottom:1px solid #eee}
.group-header h2{font-size:15px;font-weight:600}
.group-header .meta{font-size:12px;color:#888;margin-top:4px}
.group-body{display:grid;grid-template-columns:1fr 2fr;gap:20px}
.original-section{border-right:2px solid #e8f5e9;padding-right:20px}
.section-label{font-size:11px;text-transform:uppercase;letter-spacing:1px;
               font-weight:700;margin-bottom:10px}
.original-section .section-label{color:#2e7d32}
.duplicates-section .section-label{color:#ef6c00}
.duplicates-grid{display:flex;flex-wrap:wrap;gap:14px}
.card{border:1px solid #e0e0e0;border-radius:6px;padding:8px;
      background:#fafafa;text-align:center;max-width:350px}
.card.original{border-color:#a5d6a7;background:#f1f8e9;max-width:350px}
.card img{height:220px;width:auto;object-fit:contain;
          display:block;margin:0 auto 6px}
.card .info{font-size:11px;color:#555;line-height:1.5}
.card .info span{display:block}
.card .score{display:inline-block;padding:2px 8px;border-radius:10px;
             font-size:10px;font-weight:700;margin-top:4px}
.score-high{background:#c8e6c9;color:#2e7d32}
.score-medium{background:#fff9c4;color:#f57f17}
.score-low{background:#ffcdd2;color:#c62828}
"""


def score_class(score):
    if score is None:
        return ""
    if score >= 0.95:
        return "score-high"
    if score >= 0.85:
        return "score-medium"
    return "score-low"

def format_bytes(size):
    """Форматирует байты в KiB, MiB, GiB и т.д."""
    if size == 0:
        return "0 B"
    
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    
    return f"{size:.1f} {units[i]}"

def make_card(item, is_original=False):
    score = item.get('score')
    score_html = ""
    if score is not None:
        score_html = f'<span class="score {score_class(score)}">{score:.3f}</span>'

    w, h, s = item.get('width', '?'), item.get('height', '?'), format_bytes(int(item.get('file_size', '?')))
    added = item.get('added_at', '')[:19].replace('T', ' ')
    css = 'original' if is_original else ''

    return f"""
    <div class="card {css}">
        <img src="{item['path']}" alt="" loading="lazy">
        <div class="info">
            <span>{w}×{h}&nbsp;{s}</span>
            <span>{added}</span>
            {score_html}
        </div>
    </div>"""


def main():
    data = json.loads(sys.stdin.read())

    groups_html = []
    for i, g in enumerate(data['groups'], 1):
        orig = make_card({
            'path': g['original_path'],
            'width': g.get('original_width'),
            'height': g.get('original_height'),
            'file_size': g.get('original_file_size'),
            'added_at': g.get('original_added_at', ''),
        }, is_original=True)

        dups = ''.join(make_card(d) for d in g['duplicates'])

        groups_html.append(f"""
        <div class="group">
            <div class="group-header">
                <h2>Группа #{i} — original_id: {g['original_id']}</h2>
                <div class="meta">{len(g['duplicates'])} дубликат(ов)</div>
            </div>
            <div class="group-body">
                <div class="original-section">
                    <div class="section-label">★ Оригинал</div>
                    {orig}
                </div>
                <div class="duplicates-section">
                    <div class="section-label">Дубликаты</div>
                    <div class="duplicates-grid">{dups}</div>
                </div>
            </div>
        </div>""")

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Отчёт по дубликатам</title>
<style>{CSS}</style>
</head>
<body>
<h1>Группы дубликатов</h1>
<p class="summary">Всего групп: {data['total_duplicate_groups']} &ensp;|&ensp; {datetime.now():%Y-%m-%d %H:%M}</p>
{''.join(groups_html)}
</body>
</html>"""

    Path('report.html').write_text(html, encoding='utf-8')
    print(f"✅ report.html")


if __name__ == '__main__':
    main()
