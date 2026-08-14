"""自选股管理（SQLite 持久化）"""
import sqlite3
from datetime import datetime

from config import DB_PATH


class Watchlist:
    """自选股列表管理"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    code     TEXT PRIMARY KEY,
                    name     TEXT,
                    market   TEXT,
                    added_at TEXT
                )
            """)
            conn.commit()

    def add(self, code: str, name: str = "", market: str = "") -> bool:
        """添加自选，返回是否新增"""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO watchlist (code, name, market, added_at) "
                    "VALUES (?,?,?,?)",
                    (code, name, market, datetime.now().isoformat(timespec="seconds")),
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception:
            return False

    def remove(self, code: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM watchlist WHERE code=?", (code,))
            conn.commit()
            return cur.rowcount > 0

    def get_all(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT code, name, market, added_at FROM watchlist ORDER BY added_at"
            ).fetchall()
        return [{"code": r[0], "name": r[1], "market": r[2], "added_at": r[3]}
                for r in rows]

    def contains(self, code: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM watchlist WHERE code=?", (code,)).fetchone()
        return row is not None

    def clear(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM watchlist")
            conn.commit()


watchlist = Watchlist()
