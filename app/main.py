from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import Settings, load_settings
from .format import format_event
from .notify import TelegramNotifier
from .ratelimit import RateLimiter
from .security import verify_signature
from .store import EventStore


def create_app(settings: Settings | None = None, notifier: TelegramNotifier | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = EventStore(settings.db_path)
    limiter = RateLimiter(settings.rate_limit_per_minute)
    if notifier is None and settings.telegram_enabled:
        notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)

    app = FastAPI(title="webhook-relay", version="1.0.0")
    app.state.settings = settings
    app.state.store = store
    app.state.notifier = notifier

    @app.get("/health")
    async def health():
        return {"status": "ok", "telegram": bool(notifier)}

    @app.get("/events")
    async def events(limit: int = 20):
        return {"events": store.list_events(min(limit, 100))}

    @app.post("/webhook/{source}")
    async def webhook(source: str, request: Request):
        body = await request.body()

        # 1. Authenticate: every sender must sign the raw body with the shared secret.
        sig = request.headers.get("X-Hub-Signature-256")
        if not verify_signature(settings.webhook_secret, body, sig):
            return JSONResponse({"ok": False, "error": "invalid signature"}, status_code=401)

        # 2. Rate limit per source.
        if not limiter.allow(source):
            return JSONResponse({"ok": False, "error": "rate limited"}, status_code=429)

        # 3. Deduplicate on the delivery id when the sender provides one.
        delivery_id = request.headers.get("X-GitHub-Delivery") or request.headers.get("X-Delivery-Id")
        if store.is_duplicate(delivery_id):
            return {"ok": True, "duplicate": True}

        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)

        event_type = request.headers.get("X-GitHub-Event", "")
        summary = format_event(source, event_type, payload)
        store.add_event(delivery_id, source, event_type or "event", summary, payload)

        # 4. Notify. A failed Telegram call never fails the webhook itself.
        sent = False
        if notifier:
            sent = await notifier.send(summary)
        return {"ok": True, "notified": sent, "summary": summary}

    return app


app = create_app()
