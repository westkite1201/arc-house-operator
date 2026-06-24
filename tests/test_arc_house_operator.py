import supervised_opener
import daily_report


def test_extract_content_filters_official_content_links():
    html = '''
    <a href="/en/public/blogs/arc-transaction-memos">Arc Transaction Memos</a>
    <a href="/en/public/videos/demo-video">Arc Demo Video</a>
    <a href="https://evil.example/claim">Claim now</a>
    <a href="/login">Login</a>
    '''
    reads, videos = daily_report.extract_content(html)
    assert reads == [{"type": "read", "title": "Arc Transaction Memos", "url": "https://community.arc.io/en/public/blogs/arc-transaction-memos"}]
    assert videos == [{"type": "video", "title": "Arc Demo Video", "url": "https://community.arc.io/en/public/videos/demo-video"}]


def test_supervised_html_queue_contains_safety_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(supervised_opener, "STATE_DIR", tmp_path)
    monkeypatch.setattr(supervised_opener, "HTML_OUT", tmp_path / "queue.html")
    out = supervised_opener.write_html([
        {"type": "read", "title": "Safe Official Link", "url": "https://community.arc.io/en/public/blogs/a"}
    ])
    text = out.read_text()
    assert "지갑 연결" in text
    assert "단일 운영 계정" in text
    assert "계정·지갑·프록시 순환" in text
    assert "Safe Official Link" in text
    assert "https://community.arc.io/en/public/blogs/a" in text


def test_safety_note_rejects_risky_automation_language():
    note = supervised_opener.SAFETY_NOTE.lower()
    assert "no wallet connect" in note
    assert "no captcha" in note
    assert "no points api" in note
    assert "one operator account" in note
    assert "no account/wallet/proxy rotation" in note


def test_completion_tracking_round_trip(tmp_path, monkeypatch):
    completions_path = tmp_path / "completions.json"
    monkeypatch.setattr(supervised_opener, "COMPLETIONS_PATH", completions_path)
    item = {"type": "read", "title": "Arc Memo", "url": "https://community.arc.io/en/public/blogs/memo"}

    record = supervised_opener.mark_completed(item, mode="test")

    assert record["mode"] == "test"
    assert supervised_opener.load_completions()[item["url"]]["title"] == "Arc Memo"
    assert supervised_opener.pending_links([item]) == []


def test_guided_completion_records_operator_evidence(tmp_path, monkeypatch):
    completions_path = tmp_path / "completions.json"
    monkeypatch.setattr(supervised_opener, "COMPLETIONS_PATH", completions_path)
    item = {"type": "read", "title": "Arc Memo", "url": "https://community.arc.io/en/public/blogs/memo"}

    record = supervised_opener.mark_completed_with_evidence(
        item,
        mode="operator_confirmed_guided",
        evidence={
            "operator_elapsed_seconds": 61.2,
            "minimum_guidance_seconds": 45,
            "operator_note": "read manually",
        },
    )

    stored = supervised_opener.load_completions()[item["url"]]
    assert record["mode"] == "operator_confirmed_guided"
    assert stored["operator_elapsed_seconds"] == 61.2
    assert stored["minimum_guidance_seconds"] == 45
    assert stored["operator_note"] == "read manually"


def test_pending_links_filters_completed(tmp_path, monkeypatch):
    completions_path = tmp_path / "completions.json"
    monkeypatch.setattr(supervised_opener, "COMPLETIONS_PATH", completions_path)
    done = {"type": "read", "title": "Done", "url": "https://community.arc.io/en/public/blogs/done"}
    todo = {"type": "video", "title": "Todo", "url": "https://community.arc.io/en/public/videos/todo"}
    supervised_opener.mark_completed(done, mode="test")

    assert supervised_opener.pending_links([done, todo]) == [todo]
