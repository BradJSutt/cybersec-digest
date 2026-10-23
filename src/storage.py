import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager


class Storage:
    def __init__(self, config_path="config.yaml"):
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        db_path = Path(cfg.get("database", {}).get("path", "data/digest.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    published REAL NOT NULL,
                    fetched_at REAL NOT NULL,
                    summary TEXT DEFAULT '',
                    category TEXT DEFAULT 'news',
                    image_url TEXT DEFAULT '',
                    feed_category TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_start TEXT NOT NULL,
                    week_end TEXT NOT NULL,
                    pdf_path TEXT DEFAULT '',
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    clicked_at REAL NOT NULL,
                    subscriber TEXT DEFAULT '',
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                );

                CREATE TABLE IF NOT EXISTS subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    created_at REAL NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published);
                CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
                CREATE INDEX IF NOT EXISTS idx_clicks_article ON clicks(article_id);
            """)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def insert_article(self, url, title, source, published, image_url="", feed_category=""):
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO articles (url, title, source, published, fetched_at, image_url, feed_category)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (url, title, source, published, time.time(), image_url, feed_category)
            )
            return cursor.rowcount > 0

    def get_recent_articles(self, lookback_days=7, limit=50):
        cutoff = time.time() - (lookback_days * 86400)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM articles WHERE published > ? ORDER BY published DESC LIMIT ?",
                (cutoff, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_articles_between(self, start_ts, end_ts, limit=200):
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM articles
                   WHERE published >= ? AND published <= ?
                   ORDER BY published DESC LIMIT ?""",
                (start_ts, end_ts, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_article_count_between(self, start_ts, end_ts):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM articles WHERE published >= ? AND published <= ?",
                (start_ts, end_ts)
            ).fetchone()
            return row["n"]

    def update_summary(self, article_id, summary, category):
        with self._connect() as conn:
            conn.execute(
                "UPDATE articles SET summary = ?, category = ? WHERE id = ?",
                (summary, category, article_id)
            )

    def update_image(self, article_id, image_url):
        with self._connect() as conn:
            conn.execute(
                "UPDATE articles SET image_url = ? WHERE id = ?",
                (image_url, article_id)
            )

    def get_article_by_id(self, article_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            return dict(row) if row else None

    def record_click(self, article_id, subscriber=""):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO clicks (article_id, clicked_at, subscriber) VALUES (?, ?, ?)",
                (article_id, time.time(), subscriber)
            )

    def get_click_counts(self):
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT a.category, COUNT(c.id) as click_count
                   FROM articles a
                   JOIN clicks c ON c.article_id = a.id
                   GROUP BY a.category"""
            ).fetchall()
            return {r["category"]: r["click_count"] for r in rows}

    def create_issue(self, week_start, week_end, pdf_path=""):
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id FROM issues WHERE week_start = ? AND week_end = ?
                   ORDER BY id DESC LIMIT 1""",
                (week_start, week_end),
            ).fetchone()
            now = time.time()
            if row:
                conn.execute(
                    "UPDATE issues SET pdf_path = ?, created_at = ? WHERE id = ?",
                    (pdf_path, now, row["id"]),
                )
                return row["id"]
            cur = conn.execute(
                "INSERT INTO issues (week_start, week_end, pdf_path, created_at) VALUES (?, ?, ?, ?)",
                (week_start, week_end, pdf_path, now)
            )
            return cur.lastrowid

    def get_issue_by_week(self, week_start, week_end):
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM issues WHERE week_start = ? AND week_end = ?
                   ORDER BY id DESC LIMIT 1""",
                (week_start, week_end),
            ).fetchone()
            return dict(row) if row else None

    def get_latest_issue(self):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM issues ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def get_issue_by_id(self, issue_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
            return dict(row) if row else None

    def get_all_issues(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM issues ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_archive_issues(self):
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM issues
                   WHERE id IN (SELECT MAX(id) FROM issues GROUP BY week_start, week_end)
                   ORDER BY week_end DESC, id DESC"""
            ).fetchall()
            return [dict(r) for r in rows]

    def add_subscriber(self, email):
        with self._connect() as conn:
            row = conn.execute("SELECT id, active FROM subscribers WHERE email = ?", (email,)).fetchone()
            if row:
                if row["active"]:
                    return "exists"
                conn.execute("UPDATE subscribers SET active = 1 WHERE id = ?", (row["id"],))
                return "reactivated"
            conn.execute(
                "INSERT INTO subscribers (email, created_at, active) VALUES (?, ?, 1)",
                (email, time.time())
            )
            return "added"

    def deactivate_subscriber(self, email):
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE subscribers SET active = 0 WHERE email = ? AND active = 1", (email,)
            )
            return cursor.rowcount > 0

    def get_active_subscribers(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT email FROM subscribers WHERE active = 1 ORDER BY created_at"
            ).fetchall()
            return [r["email"] for r in rows]

    def get_subscriber_count(self):
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) AS n FROM subscribers WHERE active = 1"
            ).fetchone()["n"]
