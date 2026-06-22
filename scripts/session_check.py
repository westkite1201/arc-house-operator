#!/usr/bin/env python3
"""Check Arc House browser-profile session health without doing account actions."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

BASE = "https://community.arc.io"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_DIR = REPO_ROOT / ".browser-profiles/arc-house"
PROFILE_DIR = Path(os.environ.get("ARC_HOUSE_BROWSER_PROFILE", str(DEFAULT_PROFILE_DIR)))


def check_session(headed: bool = False) -> tuple[bool, str]:
    from playwright.sync_api import sync_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=not headed,
            executable_path="/usr/bin/chromium-browser",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            page = context.new_page()
            page.goto(BASE, wait_until="domcontentloaded", timeout=45_000)
            text = page.locator("body").inner_text(timeout=10_000)
            url = page.url
        finally:
            context.close()
    login_needed = bool(re.search(r"sign in|log in|login|connect|가입|로그인", text, re.I))
    # Conservative: this only says whether the browser profile can load the page and whether login-looking text appears.
    if login_needed:
        return False, f"login_or_connect_prompt_seen url={url} profile={PROFILE_DIR}"
    return True, f"page_loaded_no_obvious_login_prompt url={url} profile={PROFILE_DIR}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    ok, msg = check_session(headed=args.headed)
    print(f"session_ok={str(ok).lower()} {msg}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
