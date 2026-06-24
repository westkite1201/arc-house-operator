# Single-account runbook

Arc House Operator is designed for one operator account and one dedicated testnet/browser profile.

## Default posture

Use:

- one Arc House account
- one dedicated browser profile
- one testnet wallet if a wallet is ever needed manually
- official Arc/Circle domains only

Do not use this repo to rotate accounts, rotate wallets, rotate proxies, or manufacture engagement signals.

## Why not multi-account rotation

Multi-account automation makes the operator footprint easier to cluster:

- shared browser/runtime fingerprints
- repeated timing and page-order patterns
- shared faucet or funding history
- identical content/read/watch loops
- repeated local completion state shapes

Even on testnets, those signals can be treated as Sybil or points-farming evidence if rewards, allowlists, roles, or retroactive scoring are introduced later.

## Automation boundary

Allowed:

- collect official links
- generate a local queue
- open official pages in one persistent profile
- check public rules/token/RPC/faucet/explorer status
- record local completion notes

Manual only:

- login
- wallet connect
- signatures
- faucet claim
- CAPTCHA
- posting/commenting/submission
- claim or airdrop pages

Never automate:

- account switching
- wallet switching
- proxy/IP rotation
- direct points API calls
- hidden event calls
- session cookie export/import

## Recommended daily flow

```bash
python3 scripts/daily_report.py
python3 scripts/supervised_opener.py --skip-completed --interactive
```

For a supervised browser session:

```bash
python3 scripts/supervised_opener.py --browser --headed --skip-completed
```

Keep the browser open, perform required login/read/watch actions manually, and close it when done.
