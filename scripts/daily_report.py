#!/usr/bin/env python3
"""Daily Arc House operator report for Telegram.

Safe automation only: fetches public official pages, builds a checklist,
checks official status text/RPC availability, and remembers diffs locally.
No login, no wallet, no posting, no point/API spoofing.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE = "https://community.arc.io"
CONTENT_URL = f"{BASE}/en/public/content"
RULES_URL = f"{BASE}/public/contributors/contribution-rules"
TOKEN_URL = "https://www.arc.io/arc-token-whitepaper"
RPC_URL = "https://rpc.testnet.arc.network"
FAUCET_URL = "https://faucet.circle.com/"
EXPLORER_URL = "https://testnet.arcscan.app"
DEFAULT_STATE_DIR = Path(__file__).resolve().parents[1] / "state"
STATE_DIR = Path(__import__("os").environ.get("ARC_HOUSE_STATE_DIR", str(DEFAULT_STATE_DIR)))
STATE_PATH = STATE_DIR / "arc_house_daily_state.json"
COMPLETIONS_PATH = STATE_DIR / "completions.json"

UA = "Mozilla/5.0 (Hermes Arc House safe monitor; public pages only)"


def fetch(url: str, timeout: int = 25) -> tuple[int | None, str, str | None]:
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json,*/*"})
        with urlopen(req, timeout=timeout) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            return r.status, r.read().decode(charset, errors="replace"), None
    except HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, body, str(e)
    except URLError as e:
        return None, "", str(e)
    except Exception as e:
        return None, "", repr(e)


def post_json_rpc() -> tuple[bool, str]:
    import urllib.request

    payload = json.dumps({"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}).encode()
    try:
        req = urllib.request.Request(
            RPC_URL,
            data=payload,
            headers={"User-Agent": UA, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        chain_id = data.get("result")
        return chain_id == "0x4cef52", f"chainId={chain_id}"
    except Exception as e:
        return False, str(e)[:160]


def clean_text(s: str) -> str:
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def link_text(raw: str) -> str:
    t = clean_text(raw)
    # Webflow sometimes leaks CSS in anchors; trim obvious junk.
    t = re.sub(r"\.css-[^ ]+\{.*", "", t).strip()
    return t


def extract_content(html_text: str):
    items = []
    seen = set()
    for href, raw in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.I | re.S):
        href = html.unescape(href)
        if not href.startswith("/"):
            continue
        if not re.search(r"/en/public/(videos|blogs|resources|externals)/", href):
            continue
        title = link_text(raw)
        if not title or len(title) < 8 or title.startswith(".css"):
            continue
        url = urljoin(BASE, href)
        key = url.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        typ = "video" if "/videos/" in href else "read"
        items.append({"type": typ, "title": title[:140], "url": key})
    reads = [x for x in items if x["type"] == "read"][:5]
    videos = [x for x in items if x["type"] == "video"][:4]
    return reads, videos


def summarize_rules(text: str) -> str:
    keys = ["Daily Active", "Read Content", "Watch a Video", "Publish a Post", "Accepted Answer", "Finish Onboarding"]
    bits = []
    for k in keys:
        i = text.lower().find(k.lower())
        if i >= 0:
            snippet = text[i : i + 220]
            snippet = re.sub(r"\s+", " ", snippet).strip()
            bits.append(snippet)
    return " | ".join(bits)


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:12]


def load_state():
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def load_completions():
    try:
        return json.loads(COMPLETIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def ok_page(url: str) -> tuple[bool, str]:
    status, _body, err = fetch(url, timeout=12)
    if status and 200 <= status < 400:
        return True, f"HTTP {status}"
    return False, f"HTTP {status or 'ERR'} {err or ''}".strip()


def main() -> int:
    state = load_state()
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

    c_status, c_html, c_err = fetch(CONTENT_URL)
    reads, videos = extract_content(c_html) if c_status == 200 else ([], [])

    r_status, r_html, r_err = fetch(RULES_URL)
    rules_text = clean_text(r_html) if r_status == 200 else ""
    rules_summary = summarize_rules(rules_text)
    rules_hash = sha(rules_summary) if rules_summary else "ERR"
    rules_changed = bool(state.get("rules_hash") and state.get("rules_hash") != rules_hash)

    t_status, t_html, t_err = fetch(TOKEN_URL)
    token_text = clean_text(t_html) if t_status == 200 else ""
    not_launched = bool(re.search(r"ARC (token )?(has )?not launched|ARC is not launched|No ARC token has been launched", token_text, re.I))
    no_final = bool(re.search(r"no final decision has been made|No decision has been made", token_text, re.I))
    status_summary = f"not_launched={not_launched}; no_final_decision={no_final}"
    token_hash = sha(status_summary)
    token_changed = bool(state.get("token_hash") and state.get("token_hash") != token_hash)

    rpc_ok, rpc_msg = post_json_rpc()
    faucet_ok, faucet_msg = ok_page(FAUCET_URL)
    explorer_ok, explorer_msg = ok_page(EXPLORER_URL)

    read_urls = [x["url"] for x in reads]
    video_urls = [x["url"] for x in videos]
    completions = load_completions()
    pending_count = sum(1 for url in read_urls + video_urls if url not in completions)
    completed_count = sum(1 for url in read_urls + video_urls if url in completions)
    new_reads = [x for x in reads if x["url"] not in state.get("seen_urls", [])]
    new_videos = [x for x in videos if x["url"] not in state.get("seen_urls", [])]

    lines = []
    lines.append("Arc House 오늘 루틴")
    lines.append(f"기준: {now}")
    lines.append("")
    lines.append("공식 상태")
    lines.append(f"- ARC 토큰: {'미출시/미확정 유지' if not_launched and no_final else '⚠️ 공식 문구 변화 가능 — 직접 확인 필요'}")
    lines.append(f"- Rules: {'변경 감지 ⚠️' if rules_changed else '변경 없음'}")
    lines.append(f"- Arc RPC: {'정상' if rpc_ok else '이상'} ({rpc_msg})")
    lines.append(f"- Faucet: {'접속 가능' if faucet_ok else '확인 필요'} ({faucet_msg})")
    lines.append(f"- Explorer: {'접속 가능' if explorer_ok else '확인 필요'} ({explorer_msg})")
    lines.append(f"- Queue: 완료 {completed_count} / 미완료 {pending_count}")
    lines.append("")
    lines.append("읽을 콘텐츠 5개")
    if reads:
        for idx, x in enumerate(reads, 1):
            mark = "NEW " if x in new_reads else ""
            lines.append(f"{idx}. {mark}{x['title']}\n   {x['url']}")
    else:
        lines.append(f"- 콘텐츠 수집 실패: HTTP {c_status or 'ERR'} {c_err or ''}")
    lines.append("")
    lines.append("볼 영상 4개")
    if videos:
        for idx, x in enumerate(videos, 1):
            mark = "NEW " if x in new_videos else ""
            lines.append(f"{idx}. {mark}{x['title']}\n   {x['url']}")
    else:
        lines.append(f"- 영상 수집 실패: HTTP {c_status or 'ERR'} {c_err or ''}")
    lines.append("")
    lines.append("수동 체크")
    lines.append("- Arc House 로그인 후 위 링크를 직접 열기")
    lines.append("- 영상은 페이지 로딩만 믿지 말고 재생 확인")
    lines.append("- 포스트/댓글/지갑연결/클레임은 자동화하지 않기")
    lines.append("- ARC claim / airdrop checker / seed phrase 요구 링크 금지")
    lines.append("")
    lines.append("반자동 브라우저 헬퍼")
    lines.append("- HTML queue: /home/ubuntu/repos/arc-house-operator/state/arc_house_today_links.html")
    lines.append("- Desktop/VNC에서 실행: /home/ubuntu/repos/arc-house-operator/scripts/supervised_opener.py --browser --headed")
    lines.append("- 자동 page-walk: /home/ubuntu/repos/arc-house-operator/scripts/supervised_opener.py --skip-completed --auto-walk --mark-complete --headed")
    lines.append("- 세션 체크: /home/ubuntu/repos/arc-house-operator/scripts/session_check.py --headed")

    if rules_changed and state.get("rules_summary"):
        lines.append("")
        lines.append("Rules 이전 요약")
        lines.append(f"- {state.get('rules_summary')[:900]}")
        lines.append("Rules 현재 요약")
        lines.append(f"- {rules_summary[:900]}")

    state.update(
        {
            "rules_hash": rules_hash,
            "rules_summary": rules_summary,
            "token_hash": token_hash,
            "token_status": status_summary,
            "seen_urls": sorted(set(state.get("seen_urls", []) + read_urls + video_urls))[-200:],
            "last_run_utc": now,
        }
    )
    save_state(state)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
