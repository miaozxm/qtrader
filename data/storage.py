"""SQLite 本地缓存"""
import sqlite3
from contextlib import contextmanager

import pandas as pd

from config import DB_PATH


class SQLiteStorage:
    """K线数据本地缓存，避免重复网络请求"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bars (
                    secid   TEXT NOT NULL,
                    period  TEXT NOT NULL,
                    fqt     TEXT NOT NULL,
                    date    TEXT NOT NULL,
                    open    REAL, high REAL, low REAL, close REAL,
                    volume  REAL, amount REAL,
                    PRIMARY KEY (secid, period, fqt, date)
                )
            """)
            conn.commit()

    def save_bars(self, secid: str, period: str, fqt: str, df: pd.DataFrame):
        """保存K线数据到缓存"""
        if df.empty:
            return
        rows = [
            (
                secid, period, fqt,
                str(row.date.date()) if hasattr(row.date, "date") else str(row.date),
                row.open, row.high, row.low, row.close, row.volume, row.amount,
            )
            for row in df.itertuples()
        ]
        with self._connect() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO bars
                (secid, period, fqt, date, open, high, low, close, volume, amount)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, rows)
            conn.commit()

    def load_bars(self, secid: str, period: str, fqt: str) -> pd.DataFrame:
        """从缓存读取K线"""
        with self._connect() as conn:
            df = pd.read_sql_query(
                "SELECT date, open, high, low, close, volume, amount "
                "FROM bars WHERE secid=? AND period=? AND fqt=? "
                "ORDER BY date", conn,
                params=(secid, period, fqt),
            )
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        return df

    def clear(self, secid: str = None, period: str = None, fqt: str = None):
        """清理缓存（可筛选）"""
        sql = "DELETE FROM bars WHERE 1=1"
        params = []
        if secid:
            sql += " AND secid=?"; params.append(secid)
        if period:
            sql += " AND period=?"; params.append(period)
        if fqt:
            sql += " AND fqt=?"; params.append(fqt)
        with self._connect() as conn:
            conn.execute(sql, params)
            conn.commit()


storage = SQLiteStorage()
