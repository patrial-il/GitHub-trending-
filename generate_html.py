#!/usr/bin/env python3
"""
生成 GitHub Trending HTML 页面
读取当天的 JSON 缓存文件，生成包含数据的静态 HTML 文件
"""

import json
import os
import glob
from datetime import date, timedelta
from trending_cache import TrendingCache

# HTML 输出目录
HTML_DIR = "html"

# 保留最近多少天的 HTML 文件
KEEP_DAYS = 30

# 语言颜色映射
LANG_COLORS = {
    "Java": "#b07219",
    "Python": "#3776ab",
    "JavaScript": "#f1e05a",
    "TypeScript": "#2b7489",
    "Go": "#00add8",
    "Rust": "#cea617",
    "C++": "#f34b7d",
    "C": "#555555",
    "Shell": "#89e051",
    "Kotlin": "#A97BFF",
    "Ruby": "#701516",
    "Swift": "#ffac45",
    "PHP": "#4F5D95",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
}

# HTML 模板 - 静态生成，无 JavaScript 依赖
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>GitHub Trending | {date_formatted}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --bg: #0d1117;
            --card: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-dim: #8b949e;
            --blue: #58a6ff;
            --green: #238636;
            --orange: #f0883e;
            --fire: #ff7b72;
        }}

        body {{
            font-family: -apple-system, system-ui, "Helvetica Neue", sans-serif;
            background-color: var(--bg);
            color: var(--text);
            padding: 16px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 2px solid var(--border);
        }}

        h1 {{
            font-size: 1.8rem;
            color: var(--blue);
            margin-bottom: 8px;
        }}

        .cache-info {{
            font-size: 0.85rem;
            color: var(--text-dim);
        }}

        .grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
        }}

        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 16px;
            display: block;
            transition: all 0.2s;
        }}

        .card:active {{
            transform: scale(0.98);
            border-color: var(--blue);
        }}

        .rank-badge {{
            display: inline-block;
            background: var(--border);
            color: var(--orange);
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-bottom: 8px;
        }}

        .repo-name {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--blue);
            text-decoration: none;
            display: block;
            margin-bottom: 8px;
            word-break: break-word;
            transition: color 0.2s;
        }}

        .repo-name:active {{
            color: var(--green);
        }}

        .desc {{
            font-size: 0.95rem;
            color: var(--text);
            line-height: 1.5;
            margin-bottom: 12px;
            word-break: break-word;
        }}

        .meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
            margin-bottom: 12px;
            font-size: 0.85rem;
            color: var(--text-dim);
        }}

        .lang {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .lang-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }}

        .stars-today {{
            color: var(--fire);
            font-weight: bold;
        }}

        .buttons {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .btn {{
            flex: 1;
            min-width: 80px;
            padding: 8px 12px;
            border-radius: 4px;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.85rem;
            text-align: center;
            border: 1px solid transparent;
            transition: all 0.2s;
            cursor: pointer;
            display: inline-block;
        }}

        .btn-gh {{
            background: var(--border);
            color: var(--text);
            border-color: var(--blue);
        }}

        .btn-gh:active {{
            background: var(--blue);
            color: var(--bg);
        }}

        .btn-z {{
            background: var(--green);
            color: white;
        }}

        .btn-z:active {{
            opacity: 0.8;
        }}

        .btn-copy {{
            background: var(--green);
            color: white;
            border: none;
            cursor: pointer;
        }}

        .btn-copy.copied {{
            background: var(--blue);
        }}

        .toast {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--card);
            border: 1px solid var(--blue);
            color: var(--text);
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 0.9rem;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            z-index: 1000;
        }}

        .toast.show {{
            opacity: 1;
        }}

        .footer-info {{
            text-align: center;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
            font-size: 0.8rem;
            color: var(--text-dim);
        }}

        @media (max-width: 480px) {{
            body {{ padding: 12px; }}
            h1 {{ font-size: 1.5rem; }}
            .card {{ padding: 12px; }}
            .repo-name {{ font-size: 1rem; }}
            .desc {{ font-size: 0.9rem; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <h1>🔥 GitHub Trending</h1>
        <div class="cache-info">📅 {date_formatted} | ✅ 已生成：{created_at}</div>
    </header>

    <div class="grid">
        {cards}
    </div>

    <div class="footer-info">
        ✨ 已优化手机显示 | 支持邮件预览 | 点击项目卡片查看详情
    </div>
</div>

<div class="toast" id="toast">链接已复制到剪贴板</div>

<script>
    function copyLink(url) {{
        if (navigator.clipboard) {{
            navigator.clipboard.writeText(url).then(function() {{
                showToast();
            }});
        }} else {{
            // 降级方案
            var textarea = document.createElement('textarea');
            textarea.value = url;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            showToast();
        }}
    }}

    function showToast() {{
        var toast = document.getElementById('toast');
        toast.classList.add('show');
        setTimeout(function() {{
            toast.classList.remove('show');
        }}, 2000);
    }}
</script>

</body>
</html>
'''

CARD_TEMPLATE = '''
        <!-- #{rank} -->
        <div class="card">
            <div class="rank-badge">#{rank}</div>
            <a href="{url}" class="repo-name" target="_blank">{name}</a>
            <p class="desc">{desc}</p>
            <div class="meta">
                <span class="lang"><span class="lang-dot" style="background: {lang_color};"></span> {language}</span>
                <span class="stars">⭐ {total_stars}</span>
                <span class="stars-today">🔥 {stars_today}</span>
            </div>
            <div class="buttons">
                <a href="{url}" class="btn btn-gh" target="_blank">GitHub</a>
                <a href="{zread_link}" class="btn btn-z" target="_blank">Z-Read</a>
            </div>
        </div>
'''


def get_lang_color(language: str) -> str:
    """获取编程语言对应的颜色"""
    if not language:
        return "#3776ab"
    return LANG_COLORS.get(language, "#3776ab")


def parse_stars_today(stars_today: str) -> str:
    """解析 stars_today 字段，提取数字部分"""
    if not stars_today:
        return "0"
    # 格式如 "1,394 stars today" -> 提取 "1,394"
    return stars_today.replace(" stars today", "")


def generate_html(cache_data: dict) -> str:
    """生成静态 HTML 页面"""
    # 格式化日期
    cache_date = cache_data.get("cache_date", "")
    if cache_date and len(cache_date) == 8:
        date_formatted = f"{cache_date[:4]}-{cache_date[4:6]}-{cache_date[6:8]}"
    else:
        date_formatted = "Unknown"

    # 格式化创建时间
    created_at = cache_data.get("created_at", "")
    if created_at:
        try:
            # 2026-03-19T22:10:06.422598 -> 2026-03-19 22:10
            created_at = created_at[:16].replace("T", " ")
        except:
            pass

    # 生成卡片 HTML
    cards_html = ""
    repositories = cache_data.get("repositories", [])

    for repo in repositories:
        rank = repo.get("rank", 0)
        name = repo.get("name", "Unknown")
        url = repo.get("url", "#")
        desc = repo.get("description", "No description")
        language = repo.get("language", "")
        lang_color = get_lang_color(language)
        total_stars = repo.get("total_stars", "0")
        stars_today = parse_stars_today(repo.get("stars_today", ""))
        zread_link = repo.get("zread_link", "#")

        cards_html += CARD_TEMPLATE.format(
            rank=rank,
            name=name,
            url=url,
            desc=desc or "No description",
            language=language or "Unknown",
            lang_color=lang_color,
            total_stars=total_stars,
            stars_today=stars_today,
            zread_link=zread_link
        )

    return HTML_TEMPLATE.format(
        date_formatted=date_formatted,
        created_at=created_at,
        cards=cards_html
    )


def cleanup_old_html():
    """清理超过 KEEP_DAYS 天的 HTML 文件"""
    if not os.path.exists(HTML_DIR):
        return

    cutoff_date = date.today() - timedelta(days=KEEP_DAYS)
    cutoff_key = cutoff_date.strftime("%Y%m%d")

    deleted_count = 0
    for file_path in glob.glob(os.path.join(HTML_DIR, "trending_*.html")):
        # 从文件名提取日期，如 trending_20260319.html -> 20260319
        filename = os.path.basename(file_path)
        date_match = filename.replace("trending_", "").replace(".html", "")
        if len(date_match) == 8 and date_match.isdigit():
            if date_match < cutoff_key:
                os.remove(file_path)
                print(f"[DELETED] {filename}")
                deleted_count += 1

    if deleted_count > 0:
        print(f"[OK] Removed {deleted_count} old HTML files")


def main():
    """读取当天缓存，生成 HTML 文件"""
    cache = TrendingCache()
    cache_file = cache._get_cache_file_path()

    # 确保 HTML 目录存在
    if not os.path.exists(HTML_DIR):
        os.makedirs(HTML_DIR)
        print(f"[OK] Created directory: {HTML_DIR}")

    # 读取当天的 JSON 缓存
    if not os.path.exists(cache_file):
        print(f"[WARN] 今天暂无缓存数据：{cache_file}")
        cache_data = {
            'cache_date': None,
            'created_at': None,
            'repositories': [],
            'metadata': {}
        }
    else:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        print(f"[OK] 已读取缓存：{cache_file}")

    # 生成 HTML
    html_content = generate_html(cache_data)

    # 输出到文件（文件名包含日期）
    cache_date = cache_data.get("cache_date", date.today().strftime("%Y%m%d"))
    output_file = os.path.join(HTML_DIR, f'trending_{cache_date}.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"[OK] 已生成 HTML: {output_file}")
    print(f"[INFO] 数据日期：{cache_date}")

    # 清理旧 HTML 文件
    cleanup_old_html()


if __name__ == '__main__':
    main()
