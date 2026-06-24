# Arc House Operator

Safe, supervised Arc House routine tooling.

This repo keeps Arc House monitoring and browser-assist automation out of Hermes profile ad-hoc scripts so it can be tested, versioned, and reused.

## What it does

- Fetch official Arc/Circle public pages.
- Report ARC token status, rules changes, RPC/faucet/explorer health.
- Build a daily read/watch queue from official Arc House content.
- Generate a local HTML queue.
- Optionally open official links in a persistent Chromium profile for **manual** read/watch operation.

## Safety boundary

Default operating mode is **one operator account, one browser profile, one
manual testnet wallet**. See `docs/single-account-runbook.md` for the full
runbook and the rationale for avoiding multi-account rotation.

Allowed:

- Public official page monitoring.
- Link collection and local queue generation.
- Opening official links in browser tabs.
- Manual login/read/watch by the operator.

Not allowed:

- Wallet connect/sign automation.
- Seed/private-key handling.
- CAPTCHA/faucet automation.
- Posting/commenting automation.
- Points API spoofing or hidden event calls.
- Claim/airdrop checker automation.
- Account/wallet/proxy rotation.

## Quick start

```bash
python3 scripts/daily_report.py
python3 scripts/supervised_opener.py --read-limit 5 --video-limit 2
```

Desktop/VNC browser helper:

```bash
python3 scripts/supervised_opener.py --browser --headed
```

More automated operator run, still no comment/post/wallet/sign/API spoofing:

```bash
python3 scripts/session_check.py --headed
python3 scripts/supervised_opener.py --skip-completed --auto-walk --mark-complete --headed
```

This sequentially opens official links in the persistent profile, waits per page, and records local completion state in `state/completions.json`. It does **not** call points APIs or create engagement.

Manual completion mode:

```bash
python3 scripts/supervised_opener.py --skip-completed --interactive
```

State defaults to `./state`. Override if needed:

```bash
ARC_HOUSE_STATE_DIR=/tmp/arc-state python3 scripts/daily_report.py
ARC_HOUSE_BROWSER_PROFILE=/tmp/arc-profile python3 scripts/supervised_opener.py --browser --headed
```

## Hermes cron integration

The active Hermes profile can call this repo via a thin wrapper in:

```txt
~/.hermes/profiles/hari/scripts/arc_house_daily_repo.py
```

The cron job should point at `arc_house_daily_repo.py` and use `no_agent=true`.
