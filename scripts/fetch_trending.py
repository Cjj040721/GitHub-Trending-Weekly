#!/usr/bin/env python3
"""抓取本周 GitHub 新建仓库中 star 最多的项目,生成榜单并更新 README.md。

数据来源:GitHub Search API(无需第三方库,仅用 Python 标准库)。
说明:GitHub API 不提供「本周 star 增量」统计,这里采用主流榜单的近似口径 ——
     本周内新创建、且当前 star 数最高的仓库。
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TOP_N = 10   # 榜单长度
DAYS = 7     # 统计最近几天新建的项目

ROOT = Path(__file__).resolve().parent.parent
ARCHIVES_DIR = ROOT / "archives"
README = ROOT / "README.md"


def fetch_trending() -> list[dict]:
    """调用 GitHub Search API,返回本周新建、star 数最高的仓库列表。"""
    since = (date.today() - timedelta(days=DAYS)).isoformat()
    query = urllib.parse.urlencode({
        "q": f"created:>={since}",
        "sort": "stars",
        "order": "desc",
        "per_page": str(TOP_N),
    })
    url = f"https://api.github.com/search/repositories?{query}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-trending-weekly",
    }
    # 本地运行可不配;GitHub Actions 里会自动带上 GITHUB_TOKEN,限额更宽裕
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data["items"]


def render_table(repos: list[dict]) -> str:
    """把仓库列表渲染成 Markdown 表格。"""
    lines = [
        "| 排名 | 项目 | 简介 | 语言 | ⭐ Star |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i, repo in enumerate(repos, 1):
        name = f"[{repo['full_name']}]({repo['html_url']})"
        desc = (repo.get("description") or "暂无简介").replace("|", "\\|")
        lang = repo.get("language") or "-"
        stars = repo["stargazers_count"]
        lines.append(f"| {i} | {name} | {desc} | {lang} | {stars} |")
    return "\n".join(lines)


def week_id() -> str:
    """当前 ISO 周数,如 2026-W31,用作历史榜单文件名。"""
    iso = date.today().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def render_readme(table: str, archive_files: list[str]) -> str:
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M (北京时间)")
    history = "\n".join(
        f"- [{w}](archives/{w}.md)" for w in sorted(archive_files, reverse=True)
    ) or "- 暂无"
    return f"""<div align="center">

# GitHub Trending Weekly

**Fresh repositories. Ranked by stars. Archived every week.**

An automated snapshot of the {TOP_N} most-starred repositories created during the last {DAYS} days, generated with Python and GitHub Actions.

**[English](#overview) · [本周榜单](#本周榜单) · [历史榜单](#历史榜单)**

[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Weekly-2088FF?logo=githubactions&logoColor=white)](https://github.com/Cjj040721/GitHub-Trending-Weekly/actions)
[![Python](https://img.shields.io/badge/Python-Standard_Library-3776AB?logo=python&logoColor=white)](scripts/fetch_trending.py)
[![Ranking](https://img.shields.io/badge/Top-{TOP_N}_New_Repositories-2AA887)](#本周榜单)

</div>

---

<a id="overview"></a>
## 1. Overview

GitHub's Search API does not provide a weekly star-increment metric. This project uses a transparent approximation: **repositories created in the last {DAYS} days, ranked by their current star count**. Every run rewrites this homepage and preserves a dated archive.

**Last updated:** {now}, automatically generated.

<a id="本周榜单"></a>
## 2. 本周榜单({week_id()})

{table}

<a id="历史榜单"></a>
## 3. 历史榜单

{history}

## 4. 它是怎么工作的

- `scripts/fetch_trending.py`:调用 GitHub Search API,取「最近 {DAYS} 天新建、按 star 排序」的前 {TOP_N} 个仓库,重写本 README 并存档到 `archives/`。
- `.github/workflows/update.yml`:GitHub Actions 每周一上午(北京时间)自动运行脚本,有变化就自动 commit。
- 口径说明:GitHub API 不提供「本周 star 增量」,故采用「本周新建项目 star 数」作为热度近似,与多数 trending 榜单做法一致。
"""


def main() -> None:
    repos = fetch_trending()
    table = render_table(repos)

    # 存档本周榜单
    ARCHIVES_DIR.mkdir(exist_ok=True)
    archive_path = ARCHIVES_DIR / f"{week_id()}.md"
    archive_path.write_text(
        f"# {week_id()} GitHub 热门榜\n\n{table}\n", encoding="utf-8"
    )

    # 重写 README(包含最新榜单 + 历史链接)
    archive_files = [p.stem for p in ARCHIVES_DIR.glob("*.md")]
    README.write_text(render_readme(table, archive_files), encoding="utf-8")

    print(f"已更新榜单:本周共 {len(repos)} 个项目,存档 -> {archive_path.name}")


if __name__ == "__main__":
    main()
