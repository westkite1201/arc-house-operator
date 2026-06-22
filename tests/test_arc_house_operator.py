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
    assert "Safe Official Link" in text
    assert "https://community.arc.io/en/public/blogs/a" in text


def test_safety_note_rejects_risky_automation_language():
    note = supervised_opener.SAFETY_NOTE.lower()
    assert "no wallet connect" in note
    assert "no captcha" in note
    assert "no points api" in note
