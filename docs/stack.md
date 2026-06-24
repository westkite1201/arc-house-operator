# Stack

Arc House Operator is intentionally small and script-first.

## Runtime

- Python 3.11+
- Standard library for HTTP, HTML extraction, JSON state, and CLI operation
- Playwright optional browser automation using the system Chromium binary

## Browser automation

- Playwright sync API
- Persistent Chromium profile at `.browser-profiles/arc-house` by default
- Official Arc/Circle public pages only
- No wallet connect/sign automation
- No CAPTCHA/faucet automation
- No posting/commenting automation
- No points API spoofing

## State

- `state/arc_house_daily_state.json` — rules/token/content hashes and last-run state
- `state/completions.json` — local operator completion records
- `state/arc_house_today_links.html` — generated queue page

## Hermes integration

Hermes cron does not run repo internals directly. It calls the profile-local wrapper:

```txt
~/.hermes/profiles/hari/scripts/arc_house_daily_repo.py
```

That wrapper executes:

```txt
/home/ubuntu/repos/arc-house-operator/scripts/daily_report.py
```

## Test stack

- pytest
- Pure unit tests for official-link filtering, safety copy, completion tracking, and pending-link filtering

Run:

```bash
python3 -m pytest -q
```
