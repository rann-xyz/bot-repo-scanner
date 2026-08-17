import sqlite3
from pathlib import Path
from datetime import datetime, timezone


class Database:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.init()

    def connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def init(self):
        with self.connect() as con:
            con.execute(
                '''
                CREATE TABLE IF NOT EXISTS repositories (
                    github_id INTEGER PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    pushed_at TEXT,
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    language TEXT,
                    category TEXT,
                    score INTEGER DEFAULT 0,
                    reason TEXT,
                    notified_at TEXT,
                    first_seen_at TEXT NOT NULL
                )
                '''
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_repo_created ON repositories(created_at)"
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_repo_score ON repositories(score)"
            )

    def exists(self, github_id: int) -> bool:
        with self.connect() as con:
            row = con.execute(
                "SELECT 1 FROM repositories WHERE github_id = ?", (github_id,)
            ).fetchone()
            return row is not None

    def insert(self, repo: dict, category: str, score: int, reason: str):
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as con:
            con.execute(
                '''
                INSERT OR IGNORE INTO repositories
                (github_id, full_name, url, name, description, created_at,
                 updated_at, pushed_at, stars, forks, language, category,
                 score, reason, first_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    repo["id"],
                    repo["full_name"],
                    repo["html_url"],
                    repo["name"],
                    repo.get("description"),
                    repo.get("created_at"),
                    repo.get("updated_at"),
                    repo.get("pushed_at"),
                    repo.get("stargazers_count", 0),
                    repo.get("forks_count", 0),
                    repo.get("language"),
                    category,
                    score,
                    reason,
                    now,
                ),
            )

    def mark_notified(self, github_id: int):
        with self.connect() as con:
            con.execute(
                "UPDATE repositories SET notified_at = ? WHERE github_id = ?",
                (datetime.now(timezone.utc).isoformat(), github_id),
            )

    def stats(self):
        with self.connect() as con:
            total = con.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
            notified = con.execute(
                "SELECT COUNT(*) FROM repositories WHERE notified_at IS NOT NULL"
            ).fetchone()[0]
            avg = con.execute(
                "SELECT COALESCE(AVG(score), 0) FROM repositories"
            ).fetchone()[0]
            return {"total": total, "notified": notified, "avg_score": round(avg, 1)}

    def latest(self, limit: int = 10):
        with self.connect() as con:
            return con.execute(
                '''
                SELECT * FROM repositories
                ORDER BY first_seen_at DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
