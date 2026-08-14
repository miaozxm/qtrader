"""模拟交易账户（纸面交易）"""
import sqlite3
from datetime import datetime

from config import DB_PATH


class PaperAccount:
    """模拟账户：现金、持仓、成交记录（SQLite 持久化）

    - 初始资金默认 100 万
    - 支持买入/卖出/清仓
    - 记录每笔成交
    """

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_cash (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    cash REAL NOT NULL DEFAULT 1000000
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_positions (
                    code     TEXT PRIMARY KEY,
                    name     TEXT,
                    qty      REAL NOT NULL,
                    avg_cost REAL NOT NULL,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts         TEXT NOT NULL,
                    code       TEXT NOT NULL,
                    name       TEXT,
                    side       TEXT NOT NULL,
                    qty        REAL NOT NULL,
                    price      REAL NOT NULL,
                    cash_after REAL
                )
            """)
            conn.execute("INSERT OR IGNORE INTO paper_cash (id, cash) VALUES (1, 1000000)")
            conn.commit()

    # ---- 账户查询 ----
    def get_cash(self) -> float:
        with self._connect() as conn:
            row = conn.execute("SELECT cash FROM paper_cash WHERE id=1").fetchone()
        return row[0] if row else 0.0

    def get_positions(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT code, name, qty, avg_cost FROM paper_positions ORDER BY code"
            ).fetchall()
        return [{"code": r[0], "name": r[1], "qty": r[2], "avg_cost": r[3]}
                for r in rows]

    def get_trades(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, code, name, side, qty, price, cash_after "
                "FROM paper_trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"ts": r[0], "code": r[1], "name": r[2], "side": r[3],
                 "qty": r[4], "price": r[5], "cash_after": r[6]} for r in rows]

    def has_position(self, code: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM paper_positions WHERE code=?", (code,)
            ).fetchone()
        return row is not None

    # ---- 交易操作 ----
    def buy(self, code: str, name: str, qty: float, price: float) -> str:
        """按市价买入，返回消息"""
        if qty <= 0 or price <= 0:
            return "参数错误：数量或价格必须为正"
        cost = qty * price
        cash = self.get_cash()
        if cost > cash:
            return f"资金不足：需要 {cost:,.0f}，可用 {cash:,.0f}"

        with self._connect() as conn:
            # 更新现金
            conn.execute("UPDATE paper_cash SET cash = cash - ? WHERE id=1", (cost,))
            # 更新持仓（均价）
            row = conn.execute(
                "SELECT qty, avg_cost FROM paper_positions WHERE code=?",
                (code,)
            ).fetchone()
            if row:
                old_qty, old_cost = row
                new_qty = old_qty + qty
                new_cost = (old_cost * old_qty + cost) / new_qty
                conn.execute(
                    "UPDATE paper_positions SET qty=?, avg_cost=?, updated_at=? "
                    "WHERE code=?",
                    (new_qty, new_cost, datetime.now().isoformat(timespec="seconds"), code),
                )
            else:
                conn.execute(
                    "INSERT INTO paper_positions (code, name, qty, avg_cost, updated_at) "
                    "VALUES (?,?,?,?,?)",
                    (code, name, qty, price, datetime.now().isoformat(timespec="seconds")),
                )
            conn.execute(
                "INSERT INTO paper_trades (ts, code, name, side, qty, price, cash_after) "
                "VALUES (?,?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), code, name, "买入",
                 qty, price, cash - cost),
            )
            conn.commit()
        return f"买入 {code} {qty} 股 @ {price:.3f}"

    def sell(self, code: str, qty: float, price: float) -> str:
        """按市价卖出，返回消息"""
        if qty <= 0 or price <= 0:
            return "参数错误：数量或价格必须为正"
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, qty FROM paper_positions WHERE code=?", (code,)
            ).fetchone()
            if not row:
                return f"未持有 {code}"
            name, hold_qty = row
            if qty > hold_qty:
                return f"持仓不足：持有 {hold_qty}，卖出 {qty}"

            proceed = qty * price
            conn.execute("UPDATE paper_cash SET cash = cash + ? WHERE id=1", (proceed,))
            new_qty = hold_qty - qty
            if new_qty <= 1e-9:
                conn.execute("DELETE FROM paper_positions WHERE code=?", (code,))
            else:
                conn.execute(
                    "UPDATE paper_positions SET qty=?, updated_at=? WHERE code=?",
                    (new_qty, datetime.now().isoformat(timespec="seconds"), code),
                )
            conn.execute(
                "INSERT INTO paper_trades (ts, code, name, side, qty, price, cash_after) "
                "VALUES (?,?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), code, name, "卖出",
                 qty, price, self.get_cash() + proceed),
            )
            conn.commit()
        return f"卖出 {code} {qty} 股 @ {price:.3f}"

    def close_position(self, code: str, price: float) -> str:
        """清仓某标的"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT qty FROM paper_positions WHERE code=?", (code,)
            ).fetchone()
            if not row:
                return f"未持有 {code}"
        return self.sell(code, row[0], price)

    def reset(self):
        """重置账户"""
        with self._connect() as conn:
            conn.execute("UPDATE paper_cash SET cash=1000000 WHERE id=1")
            conn.execute("DELETE FROM paper_positions")
            conn.execute("DELETE FROM paper_trades")
            conn.commit()


paper_account = PaperAccount()
