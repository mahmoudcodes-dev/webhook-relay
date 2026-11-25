# webhook-relay

A small FastAPI server that receives webhooks (GitHub and any other source), verifies their HMAC signature, rate-limits them, deduplicates deliveries, and forwards a clean, human-readable summary to Telegram.

Built as a learning project for the Mahmoud Codes channel (Arabic video walkthrough linked below).

## What it does

1. **Authenticates** every request: senders sign the raw body with a shared secret and send it in `X-Hub-Signature-256` (GitHub's scheme). Bad or missing signature -> `401`.
2. **Rate limits** per source (default 60/minute, sliding window) -> `429` when exceeded.
3. **Deduplicates** on the delivery id (`X-GitHub-Delivery` or `X-Delivery-Id`) so retries are not forwarded twice.
4. **Formats** known events (GitHub push, pull_request, issues, star, ping) into short readable messages.
5. **Notifies** a Telegram chat through a bot. If Telegram is not configured or the call fails, the webhook still succeeds - alerting never breaks ingestion.
6. **Stores** every accepted delivery in SQLite (`GET /events` lists the recent ones).

## Run it

```bash
cp .env.example .env   # set WEBHOOK_SECRET, and optionally the Telegram values
docker compose up --build
```

Then:

```bash
curl http://localhost:8000/health
```

### Send a test webhook (signed)

```bash
SECRET=change-me
BODY='{"ref":"refs/heads/main","repository":{"full_name":"you/repo"},"sender":{"login":"you"},"commits":[{"message":"hello"}]}'
SIG="sha256=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')"
curl -X POST http://localhost:8000/webhook/github \
  -H 'Content-Type: application/json' \
  -H "X-Hub-Signature-256: $SIG" \
  -H 'X-GitHub-Event: push' \
  -d "$BODY"
```

## Connect GitHub

Repo -> Settings -> Webhooks -> Add webhook:

- Payload URL: `https://your-server/webhook/github`
- Content type: `application/json`
- Secret: the same `WEBHOOK_SECRET`

GitHub then sends signed requests this service can verify.

## Telegram setup

1. Create a bot with [@BotFather](https://t.me/BotFather), copy the token into `TELEGRAM_BOT_TOKEN`.
2. Message the bot once, then get your chat id from `https://api.telegram.org/bot<token>/getUpdates` and set `TELEGRAM_CHAT_ID`.

## Tests

```bash
pip install -r requirements.txt
pytest
```

The tests sign fake payloads with a test secret, check that bad/missing signatures are rejected, that duplicates and rate limits behave, and that the Telegram call is made with the formatted message (mocked, no real API needed). The GitHub Actions workflow boots the full Docker Compose stack and fires both a correctly signed and an unsigned webhook at it.
