#!/usr/bin/env python3
"""Supervised Arc House browser helper.

Safe boundary: public official pages only. It may open Arc House content tabs in a
persistent Chromium profile so the operator can log in and manually read/watch.
It never automates wallet connect, signatures, CAPTCHA/faucet, posting, comments,
claim links, or private APIs.
"""
from __future__ import annotations

import argparse
import html
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from daily_report import BASE, CONTENT_URL, fetch, extract_content  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = REPO_ROOT / "state"
DEFAULT_PROFILE_DIR = REPO_ROOT / ".browser-profiles/arc-house"
STATE_DIR = Path(__import__("os").environ.get("ARC_HOUSE_STATE_DIR", str(DEFAULT_STATE_DIR)))
PROFILE_DIR = Path(__import__("os").environ.get("ARC_HOUSE_BROWSER_PROFILE", str(DEFAULT_PROFILE_DIR)))
HTML_OUT = STATE_DIR / "arc_house_today_links.html"

SAFETY_NOTE = """Safe helper only: opens official Arc/Circle public pages for manual operation.\nNo wallet connect/sign, no CAPTCHA/faucet automation, no posting/commenting, no points API spoofing.\n"""


def collect_links(read_limit: int, video_limit: int) -> list[dict[str, str]]:
    status, body, err = fetch(CONTENT_URL)
    if status != 200:
        raise RuntimeError(f"content_fetch_failed HTTP {status or 'ERR'} {err or ''}".strip())
    reads, videos = extract_content(body)
    return reads[:read_limit] + videos[:video_limit]


def write_html(links: list[dict[str, str]]) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, item in enumerate(links, 1):
        title = html.escape(item["title"])
        url = html.escape(item["url"])
        rows.append(f'<li><b>{idx}. [{item["type"]}] {title}</b><br><a href="{url}" target="_blank" rel="noreferrer">{url}</a></li>')
    HTML_OUT.write_text(
        """<!doctype html><meta charset='utf-8'>
<title>Arc House supervised queue</title>
<style>body{font-family:system-ui;background:#0b0b11;color:#eee;max-width:920px;margin:40px auto;line-height:1.5}a{color:#7db7ff}li{margin:16px 0;padding:12px;border:1px solid #333;border-radius:10px;background:#15151d}.warn{color:#ffb45b}</style>
<h1>Arc House supervised queue</h1>
<p class='warn'>공식 링크만 수동으로 열어 읽기/시청하세요. 지갑 연결, 서명, CAPTCHA, faucet, posting/commenting, claim/airdrop checker 자동화 금지.</p>
<ol>
"""
        + "\n".join(rows)
        + "\n</ol>\n",
        encoding="utf-8",
    )
    return HTML_OUT


def open_browser(links: list[dict[str, str]], headed: bool, slow_ms: int) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("playwright_missing") from exc

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=not headed,
            executable_path="/usr/bin/chromium-browser",
            slow_mo=slow_ms,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = context.new_page()
        page.goto(BASE, wait_until="domcontentloaded", timeout=45_000)
        for item in links:
            tab = context.new_page()
            tab.goto(item["url"], wait_until="domcontentloaded", timeout=45_000)
            time.sleep(0.6)
        print(f"opened_tabs={len(links)+1} profile={PROFILE_DIR}")
        print(SAFETY_NOTE.strip())
        if headed:
            input("Manual browser is open. Press Enter here only after you finish and want to close it... ")
        context.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--read-limit", type=int, default=5)
    ap.add_argument("--video-limit", type=int, default=2)
    ap.add_argument("--browser", action="store_true", help="open Chromium tabs with a persistent Arc profile")
    ap.add_argument("--headed", action="store_true", help="show Chromium UI; requires a display/VNC")
    ap.add_argument("--slow-ms", type=int, default=150)
    args = ap.parse_args()

    links = collect_links(args.read_limit, args.video_limit)
    html_path = write_html(links)
    print(f"Arc House supervised queue ready: {html_path}")
    print(f"links={len(links)}")
    for idx, item in enumerate(links, 1):
        print(f"{idx}. [{item['type']}] {item['title']}\n   {item['url']}")
    if args.browser:
        open_browser(links, headed=args.headed, slow_ms=args.slow_ms)
    else:
        print("Browser not opened. Use --browser --headed from a desktop/VNC session, or open the HTML file manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
