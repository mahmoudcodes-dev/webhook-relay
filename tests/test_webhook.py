import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.notify import TelegramNotifier
from app.security import sign

SECRET = "test-secret"
PAYLOAD = {
    "ref": "refs/heads/main",
    "repository": {"full_name": "mahmoudcodes-dev/webhook-relay"},
    "pusher": {"name": "mahmoud"},
    "sender": {"login": "mahmoud"},
    "commits": [{"message": "add relay endpoint\n\nmore detail"}],
}


def make_client(tmp_path, rate_limit=60, with_telegram=False, telegram_calls=None):
    settings = Settings(
        webhook_secret=SECRET,
        rate_limit_per_minute=rate_limit,
        db_path=str(tmp_path / "test.db"),
        telegram_bot_token="token" if with_telegram else None,
        telegram_chat_id="chat" if with_telegram else None,
    )
    notifier = None
    if with_telegram:
        def handler(request: httpx.Request) -> httpx.Response:
            telegram_calls.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"ok": True})

        notifier = TelegramNotifier("token", "chat", transport=httpx.MockTransport(handler))
    return TestClient(create_app(settings, notifier=notifier))


def signed_post(client, payload=PAYLOAD, secret=SECRET, headers=None):
    body = json.dumps(payload).encode()
    h = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": sign(secret, body),
        "X-GitHub-Event": "push",
        "X-GitHub-Delivery": "delivery-1",
    }
    if headers:
        h.update(headers)
    return client.post("/webhook/github", content=body, headers=h)


def test_health(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_valid_signature_accepted_and_formatted(tmp_path):
    client = make_client(tmp_path)
    r = signed_post(client)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "Push to mahmoudcodes-dev/webhook-relay:main" in data["summary"]
    assert "add relay endpoint" in data["summary"]


def test_bad_signature_rejected(tmp_path):
    client = make_client(tmp_path)
    r = signed_post(client, secret="wrong-secret")
    assert r.status_code == 401


def test_missing_signature_rejected(tmp_path):
    client = make_client(tmp_path)
    body = json.dumps(PAYLOAD).encode()
    r = client.post("/webhook/github", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code == 401


def test_duplicate_delivery_not_processed_twice(tmp_path):
    client = make_client(tmp_path)
    assert signed_post(client).json().get("duplicate") is None
    r2 = signed_post(client)
    assert r2.status_code == 200 and r2.json()["duplicate"] is True
    events = client.get("/events").json()["events"]
    assert len(events) == 1


def test_rate_limit(tmp_path):
    client = make_client(tmp_path, rate_limit=2)
    codes = []
    for i in range(3):
        body = json.dumps(PAYLOAD).encode()
        r = client.post("/webhook/github", content=body, headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sign(SECRET, body),
            "X-GitHub-Delivery": f"d-{i}",
        })
        codes.append(r.status_code)
    assert codes == [200, 200, 429]


def test_telegram_notified_with_formatted_message(tmp_path):
    calls = []
    client = make_client(tmp_path, with_telegram=True, telegram_calls=calls)
    r = signed_post(client)
    assert r.status_code == 200 and r.json()["notified"] is True
    assert len(calls) == 1
    assert calls[0]["chat_id"] == "chat"
    assert "Push to" in calls[0]["text"]


def test_no_telegram_configured_still_ok(tmp_path):
    client = make_client(tmp_path)
    r = signed_post(client)
    assert r.status_code == 200 and r.json()["notified"] is False
