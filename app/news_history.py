"""Historico SQLite das noticias usadas em episodios."""

import glob
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "output", "news_history.sqlite3"
)


def _normalize_title(title):
    return re.sub(r"\s+", " ", title.lower()).strip()


def _canonical_link(link):
    parts = urlsplit(link.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, "", ""))


def _news_keys(item):
    values = [_normalize_title(item.get("title", ""))]
    link = _canonical_link(item.get("link", ""))
    if link:
        values.append(link)
    return [hashlib.sha256(value.encode("utf-8")).hexdigest() for value in values]


class NewsHistory:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS used_news (
                    news_key TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    link TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
                """
            )

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def unseen(self, news_items):
        if not news_items:
            return []
        keys = [key for item in news_items for key in _news_keys(item)]
        placeholders = ", ".join("?" for _ in keys)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT news_key FROM used_news WHERE news_key IN ({placeholders})",
                keys,
            ).fetchall()
        used_keys = {row[0] for row in rows}
        return [
            item for item in news_items
            if not used_keys.intersection(_news_keys(item))
        ]

    def mark_seen(self, news_items):
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            for item in news_items:
                for key in _news_keys(item):
                    connection.execute(
                        """
                        INSERT INTO used_news (news_key, title, source, link, first_seen, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(news_key) DO UPDATE SET last_seen = excluded.last_seen
                        """,
                        (
                            key,
                            item.get("title", ""),
                            item.get("source", ""),
                            item.get("link", ""),
                            now,
                            now,
                        ),
                    )

    def bootstrap_from_outputs(self, output_dir):
        imported = []
        pattern = os.path.join(output_dir, "*_episode.json")
        for path in glob.glob(pattern):
            try:
                with open(path, "r", encoding="utf-8") as file:
                    payload = json.load(file)
            except (OSError, json.JSONDecodeError):
                continue
            imported.extend(payload.get("script", {}).get("show_notes", []))
        self.mark_seen(imported)
        return len(imported)


def filter_unseen(news_items):
    return NewsHistory().unseen(news_items)
