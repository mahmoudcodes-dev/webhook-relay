import json
import sqlite3
import time


class EventStore:
    """SQLite log of accepted webhook deliveries, with delivery-id dedup."""

    def __init__(self, path: str = "events.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   delivery_id TEXT UNIQUE,
                   source TEXT NOT NULL,
                   event_type TEXT NOT NULL,
                   summary TEXT NOT NULL,
                   payload TEXT NOT NULL,
                   received_at REAL NOT NULL
               )"""
        )
        self.conn.commit()

    def is_duplicate(self, delivery_id: str | None) -> bool:
        if not delivery_id:
            return False
        row = self.conn.execute(
            "SELECT 1 FROM events WHERE delivery_id = ?", (delivery_id,)
        ).fetchone()
        return row is not None

    def add_event(self, delivery_id, source, event_type, summary, payload: dict) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO events (delivery_id, source, event_type, summary, payload, received_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (delivery_id, source, event_type, summary, json.dumps(payload), time.time()),
        )
        self.conn.commit()

    def list_events(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT delivery_id, source, event_type, summary, received_at"
            " FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "delivery_id": r[0],
                "source": r[1],
                "event_type": r[2],
                "summary": r[3],
                "received_at": r[4],
            }
            for r in rows
        ]
