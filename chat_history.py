"""
Persistent Chat History Storage using SQLite3.
Sessions are keyed by UUID; messages store role, content, attachments, and timestamp.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import contextmanager


class ChatHistoryManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "chat.db"
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    model TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    attachments TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            """)

    # ── Sessions ──────────────────────────────────────────────────────────────

    def create_session(self, model: str = None, title: str = "New Chat") -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, title, model, now, now),
            )
        return session_id

    def get_all_sessions(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_session(self, session_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_session_title(self, session_id: str, title: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, datetime.now().isoformat(), session_id),
            )

    def touch_session(self, session_id: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), session_id),
            )

    def delete_session(self, session_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return True

    # ── Messages ──────────────────────────────────────────────────────────────

    def add_message(self, session_id: str, role: str, content: str, attachments: List[Dict] = None) -> int:
        now = datetime.now().isoformat()
        atts_json = json.dumps(attachments or [])
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO messages (session_id, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, atts_json, now),
            )
            msg_id = cur.lastrowid
        self.touch_session(session_id)
        return msg_id

    def get_messages(self, session_id: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        result = []
        for r in rows:
            msg = dict(r)
            msg["attachments"] = json.loads(msg["attachments"])
            result.append(msg)
        return result

    def clear_messages(self, session_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self.touch_session(session_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def derive_title(self, first_user_message: str, max_len: int = 40) -> str:
        """Generate a session title from the first user message."""
        title = first_user_message.strip().replace("\n", " ")
        return title[:max_len] + ("…" if len(title) > max_len else "")
