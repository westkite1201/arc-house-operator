#!/usr/bin/env python3
"""Supervised Arc House browser helper.

Safe boundary: public official pages only. It may open Arc House content tabs in a
persistent Chromium profile so the operator can log in and manually read/watch.
It never automates wallet connect, signatures, CAPTCHA/faucet, posting, comments,
claim links, or private/points APIs.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from daily_report import BASE, CONTENT_URL, fetch, extract_content  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = REPO_ROOT / "state"
DEFAULT_PROFILE_DIR = REPO_ROOT / ".browser-profiles/arc-house"
STATE_DIR = Path(os.environ.get("ARC_HOUSE_STATE_DIR", str(DEFAULT_STATE_DIR)))
PROFILE_DIR = Path(os.environ.get("ARC_HOUSE_BROWSER_PROFILE", str(DEFAULT_PROFILE_DIR)))
HTML_OUT = STATE_DIR / "arc_house_today_links.html"
COMPLETIONS_PATH = STATE_DIR / "completions.json"

SAFETY_NOTE = """Safe helper only: opens official Arc/Circle public pages for manual operation/page-walk.\nNo wallet connect/sign, no CAPTCHA/faucet automation, no posting/commenting, no points API spoofing.\n"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def collect_links(read_limit: int, video_limit: int) -> list[dict[str, str]]:
    status, body, err = fetch(CONTENT_URL)
    if status != 200:
        raise RuntimeError(f"content_fetch_failed HTTP {status or 'ERR'} {err or ''}".strip())
    reads, videos = extract_content(body)
    return reads[:read_limit] + videos[:video_limit]


def load_completions(path: Path = COMPLETIONS_PATH) -> dict[str, dict[str, str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_completions(completions: dict[str, dict[str, str]], path: Path = COMPLETIONS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(completions, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def mark_completed(item: dict[str, str], mode: str, completions: dict[str, dict[str, str]] | None = None) -> dict[str, str]:
    completions = completions if completions is not None else load_completions()
    record = {
        "title": item["title"],
        "type": item["type"],
        "url": item["url"],
        "completed_at": utc_now(),
        "mode": mode,
    }
    completions[item["url"]] = record
    save_completions(completions)
    return record


def mark_completed_with_evidence(
    item: dict[str, str],
    mode: str,
    evidence: dict[str, str | int | float],
    completions: dict[str, dict[str, str]] | None = None,
) -> dict[str, str | int | float]:
    """Record an operator-confirmed completion with local verification evidence.

    Evidence is deliberately local and operator-entered. The helper does not
    synthesize scroll, dwell, watch, or points events.
    """
    completions = completions if completions is not None else load_completions()
    record: dict[str, str | int | float] = {
        "title": item["title"],
        "type": item["type"],
        "url": item["url"],
        "completed_at": utc_now(),
        "mode": mode,
        **evidence,
    }
    completions[item["url"]] = record  # type: ignore[assignment]
    save_completions(completions)  # type: ignore[arg-type]
    return record


def pending_links(links: list[dict[str, str]], completions: dict[str, dict[str, str]] | None = None) -> list[dict[str, str]]:
    completions = completions if completions is not None else load_completions()
    return [item for item in links if item["url"] not in completions]


def write_html(links: list[dict[str, str]]) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    completions = load_completions()
    rows = []
    for idx, item in enumerate(links, 1):
        title = html.escape(item["title"])
        url = html.escape(item["url"])
        done = completions.get(item["url"])
        status = "✅ done" if done else "⬜ pending"
        rows.append(
            f'<li><b>{idx}. {status} [{item["type"]}] {title}</b><br>'
            f'<a href="{url}" target="_blank" rel="noreferrer">{url}</a>'
            f'{"<br><small>completed_at=" + html.escape(done.get("completed_at", "")) + " mode=" + html.escape(done.get("mode", "")) + "</small>" if done else ""}'
            "</li>"
        )
    HTML_OUT.write_text(
        """<!doctype html><meta charset='utf-8'>
<title>Arc House supervised queue</title>
<style>body{font-family:system-ui;background:#0b0b11;color:#eee;max-width:920px;margin:40px auto;line-height:1.5}a{color:#7db7ff}li{margin:16px 0;padding:12px;border:1px solid #333;border-radius:10px;background:#15151d}.warn{color:#ffb45b}small{color:#999}</style>
<h1>Arc House supervised queue</h1>
<p class='warn'>공식 링크만 열어 읽기/시청하세요. 지갑 연결, 서명, CAPTCHA, faucet, posting/commenting, claim/airdrop checker 자동화 금지.</p>
<ol>
"""
        + "\n".join(rows)
        + "\n</ol>\n",
        encoding="utf-8",
    )
    return HTML_OUT


def _launch_context(headed: bool, slow_ms: int):
    from playwright.sync_api import sync_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    p = sync_playwright().start()
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=not headed,
        executable_path="/usr/bin/chromium-browser",
        slow_mo=slow_ms,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    return p, context


def open_browser(links: list[dict[str, str]], headed: bool, slow_ms: int) -> None:
    try:
        p, context = _launch_context(headed=headed, slow_ms=slow_ms)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("playwright_or_chromium_missing") from exc
    try:
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
    finally:
        context.close()
        p.stop()


def auto_walk(links: list[dict[str, str]], headed: bool, slow_ms: int, read_seconds: int, video_seconds: int, mark: bool) -> None:
    """Sequentially visit official links with the persistent profile.

    This is not event spoofing: it only loads the public content page and waits.
    If mark=True, local completion state records that the operator-run page walk was attempted.
    """
    try:
        p, context = _launch_context(headed=headed, slow_ms=slow_ms)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("playwright_or_chromium_missing") from exc
    completions = load_completions()
    try:
        page = context.new_page()
        page.goto(BASE, wait_until="domcontentloaded", timeout=45_000)
        for idx, item in enumerate(links, 1):
            wait_s = video_seconds if item["type"] == "video" else read_seconds
            print(f"auto_walk {idx}/{len(links)} [{item['type']}] wait={wait_s}s {item['title']}")
            page.goto(item["url"], wait_until="domcontentloaded", timeout=60_000)
            time.sleep(max(0, wait_s))
            if mark:
                mark_completed(item, mode="auto_walk_page_visit", completions=completions)
                print(f"marked_complete {item['url']}")
        save_completions(completions)
    finally:
        context.close()
        p.stop()


def interactive_walk(links: list[dict[str, str]]) -> None:
    completions = load_completions()
    for idx, item in enumerate(links, 1):
        print(f"\n{idx}/{len(links)} [{item['type']}] {item['title']}\n{item['url']}")
        answer = input("완료했으면 Enter, skip은 s 입력: ").strip().lower()
        if answer == "s":
            continue
        mark_completed(item, mode="operator_confirmed", completions=completions)
        print("marked_complete")
    save_completions(completions)


def guided_verification_walk(links: list[dict[str, str]], headed: bool, slow_ms: int, min_read_seconds: int, min_video_seconds: int) -> None:
    """Open official links one by one and require operator-confirmed evidence.

    This is a verification workflow, not behavior simulation: the script never
    scrolls, watches, clicks engagement controls, calls points APIs, or marks a
    page complete without an operator checkpoint.
    """
    try:
        p, context = _launch_context(headed=headed, slow_ms=slow_ms)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("playwright_or_chromium_missing") from exc
    completions = load_completions()
    try:
        page = context.new_page()
        page.goto(BASE, wait_until="domcontentloaded", timeout=45_000)
        print(SAFETY_NOTE.strip())
        print("Guided mode: 직접 읽기/시청/스크롤 후 터미널에서 확인만 기록합니다. 자동 스크롤/포인트 이벤트 없음.")
        for idx, item in enumerate(links, 1):
            min_seconds = min_video_seconds if item["type"] == "video" else min_read_seconds
            print(f"\n{idx}/{len(links)} [{item['type']}] {item['title']}\n{item['url']}")
            page.goto(item["url"], wait_until="domcontentloaded", timeout=60_000)
            started = time.monotonic()
            print(f"브라우저에서 직접 확인하세요. 최소 확인 가이드: {min_seconds}s")
            answer = input("완료 후 Enter, skip은 s: ").strip().lower()
            elapsed = round(time.monotonic() - started, 1)
            if answer == "s":
                print(f"skipped after {elapsed}s")
                continue
            if elapsed < min_seconds:
                confirm = input(f"{elapsed}s만 경과했습니다. 그래도 직접 확인 완료가 맞으면 'yes' 입력: ").strip().lower()
                if confirm != "yes":
                    print("not_marked")
                    continue
            note = input("선택 메모(읽은 섹션/영상 확인 등, 빈칸 가능): ").strip()
            evidence = {
                "operator_elapsed_seconds": elapsed,
                "minimum_guidance_seconds": min_seconds,
                "operator_note": note,
            }
            mark_completed_with_evidence(item, mode="operator_confirmed_guided", evidence=evidence, completions=completions)
            print(f"marked_complete operator_elapsed_seconds={elapsed}")
        save_completions(completions)
    finally:
        context.close()
        p.stop()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--read-limit", type=int, default=5)
    ap.add_argument("--video-limit", type=int, default=2)
    ap.add_argument("--browser", action="store_true", help="open Chromium tabs with a persistent Arc profile")
    ap.add_argument("--headed", action="store_true", help="show Chromium UI; requires a display/VNC")
    ap.add_argument("--slow-ms", type=int, default=150)
    ap.add_argument("--skip-completed", action="store_true", help="only include links not present in completions.json")
    ap.add_argument("--interactive", action="store_true", help="prompt operator to mark each link complete")
    ap.add_argument("--guided", action="store_true", help="open one official link at a time and require operator-confirmed verification evidence")
    ap.add_argument("--auto-walk", action="store_true", help="sequentially visit official links and wait; does not spoof APIs")
    ap.add_argument("--mark-complete", action="store_true", help="with --auto-walk, locally mark visited links complete")
    ap.add_argument("--read-seconds", type=int, default=45)
    ap.add_argument("--video-seconds", type=int, default=180)
    args = ap.parse_args()

    links = collect_links(args.read_limit, args.video_limit)
    if args.skip_completed:
        links = pending_links(links)
    html_path = write_html(links)
    print(f"Arc House supervised queue ready: {html_path}")
    print(f"links={len(links)} pending={len(pending_links(links))}")
    for idx, item in enumerate(links, 1):
        done = " done" if item["url"] in load_completions() else ""
        print(f"{idx}. [{item['type']}]{done} {item['title']}\n   {item['url']}")
    if args.interactive:
        interactive_walk(links)
    elif args.guided:
        guided_verification_walk(links, headed=args.headed, slow_ms=args.slow_ms, min_read_seconds=args.read_seconds, min_video_seconds=args.video_seconds)
    elif args.auto_walk:
        print("WARNING: --auto-walk only loads official pages. Prefer --guided for operator-confirmed verification evidence.")
        auto_walk(links, headed=args.headed, slow_ms=args.slow_ms, read_seconds=args.read_seconds, video_seconds=args.video_seconds, mark=args.mark_complete)
    elif args.browser:
        open_browser(links, headed=args.headed, slow_ms=args.slow_ms)
    else:
        print("Browser not opened. Use --browser --headed, --guided --headed, --auto-walk, or open the HTML file manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
