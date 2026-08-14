"""全市场选股器：基于技术指标的多条件筛选"""
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from data.fetcher import fetcher
from indicators.ta import add_indicators


# 选股条件：输入指标化后的K线DataFrame，返回 bool
CONDITIONS = {
    "均线多头排列": lambda df: (
        df["MA5"].iloc[-1] > df["MA10"].iloc[-1]
        > df["MA20"].iloc[-1] > df["MA60"].iloc[-1]
    ),
    "MACD金叉": lambda df: (
        df["DIF"].iloc[-1] > df["DEA"].iloc[-1]
        and df["DIF"].iloc[-2] <= df["DEA"].iloc[-2]
    ),
    "RSI超卖": lambda df: df["RSI"].iloc[-1] < 30,
    "突破布林上轨": lambda df: df["close"].iloc[-1] > df["BOLL_UP"].iloc[-1],
    "放量上涨": lambda df: (
        df["close"].iloc[-1] > df["close"].iloc[-2]
        and df["volume"].iloc[-1] > df["volume"].iloc[-2] * 1.5
    ),
}


class Screener:
    """选股器

    Example:
        s = Screener()
        hits = s.scan(market="A股", limit=100, conditions=["均线多头排列", "放量上涨"])
    """

    def __init__(self, data_fetcher=None):
        self.fetcher = data_fetcher or fetcher

    def get_universe(self, market: str = "A股", limit: int = 100) -> list[dict]:
        """获取股票池（默认按成交额取活跃股，保证可扫且有流动性）"""
        df = self.fetcher.get_stock_list(market, limit=limit,
                                         sort_field="f6", sort_desc=True)
        if df.empty:
            return []
        return [{"code": r.code, "name": r.name} for r in df.itertuples()]

    def _fetch_kline(self, stock: dict) -> dict | None:
        """拉取单只股票日K并计算指标"""
        try:
            df = self.fetcher.get_kline_by_code(
                stock["code"], period="day", fqt="qfq", beg="0"
            )
            if df is None or df.empty or len(df) < 70:
                return None
            return {"code": stock["code"], "name": stock["name"], "df": df}
        except Exception:
            return None

    def scan(self, market: str = "A股", limit: int = 100,
             conditions: list[str] | None = None,
             max_workers: int = 8, progress=None) -> pd.DataFrame:
        """扫描全市场，返回命中候选池

        Args:
            market: A股 / 港股
            limit: 扫描股票数量（按成交额取前 N 名）
            conditions: 选股条件名列表，全部命中才入选
            max_workers: 并发拉取线程数
            progress: 可选回调 progress(done, total)，用于 UI 进度

        Returns:
            DataFrame[code, name, price, pct_chg, matched, details]
        """
        conds = conditions or list(CONDITIONS.keys())
        universe = self.get_universe(market, limit)
        total = len(universe)
        if total == 0:
            return pd.DataFrame()

        rows = []
        done = 0
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(self._fetch_kline, s): s for s in universe}
            for fut in as_completed(futures):
                done += 1
                if progress:
                    progress(done, total)
                item = fut.result()
                if item is None:
                    continue
                dfi = add_indicators(item["df"])
                if len(dfi) < 70:
                    continue

                matched = []
                for name in conds:
                    fn = CONDITIONS.get(name)
                    if fn and fn(dfi):
                        matched.append(name)

                if matched:
                    last = dfi.iloc[-1]
                    prev = dfi.iloc[-2]
                    pct = (last["close"] / prev["close"] - 1) * 100
                    rows.append({
                        "code": item["code"],
                        "name": item["name"],
                        "price": round(float(last["close"]), 3),
                        "pct_chg": round(float(pct), 2),
                        "volume_ratio": round(float(
                            last["volume"] / (dfi["volume"].iloc[-6:-1].mean() or 1)), 2),
                        "RSI": round(float(last.get("RSI", 0)), 1),
                        "matched": len(matched),
                        "details": " + ".join(matched),
                    })

        if not rows:
            return pd.DataFrame()
        out = pd.DataFrame(rows)
        out = out.sort_values("pct_chg", ascending=False).reset_index(drop=True)
        return out
