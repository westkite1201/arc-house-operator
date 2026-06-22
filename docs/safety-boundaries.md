# Safety Boundaries

This repo is for supervised Arc House operations only.

## Hard no

- Do not store or request seed phrases/private keys.
- Do not automate wallet connect or message/transaction signatures.
- Do not bypass CAPTCHA or automate faucets.
- Do not call private/undocumented points APIs.
- Do not spoof read/watch/player events.
- Do not auto-post, auto-comment, or generate engagement spam.
- Do not open unknown claim/checker links.

## Safe automation pattern

1. Monitor official public sources.
2. Build a queue of official content links.
3. Open links in a persistent browser profile if the operator explicitly runs the helper.
4. Let the operator manually log in, read, watch, and decide whether to post/comment.
5. Log only public URLs, hashes, and non-sensitive state.

## Official domains used

- `https://community.arc.io`
- `https://www.arc.io`
- `https://rpc.testnet.arc.network`
- `https://faucet.circle.com`
- `https://testnet.arcscan.app`
