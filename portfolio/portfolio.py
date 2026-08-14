"""组合净值计算：多标的等权日频组合"""
import pandas as pd

from data.fetcher import fetcher
from data.storage import storage
from data.symbols import to_secid


def load_bars_cached(code: str, period: str = "day", fqt: str = "qfq",
                     beg: str = "0") -> pd.DataFrame:
    """按代码取K线（优先缓存）"""
    secid = to_secid(code)
    df = storage.load_bars(secid, period, fqt)
    if df.empty:
        df = fetcher.get_kline(secid, period, fqt, beg=beg)
        if not df.empty:
            storage.save_bars(secid, period, fqt, df)
    return df


def portfolio_returns(codes: list[str], period: str = "day", fqt: str = "qfq",
                      beg: str = "0", method: str = "equal") -> pd.DataFrame:
    """计算组合日收益率

    Args:
        codes: 股票代码列表
        method: equal 等权 / 保留

    Returns:
        DataFrame[index=date, cols=各代码收益率, 组合列=组合收益率]
    """
    if not codes:
        return pd.DataFrame()

    rets = []
    valid_codes = []
    for code in codes:
        df = load_bars_cached(code, period, fqt, beg)
        if df.empty or len(df) < 2:
            continue
        r = df.set_index("date")["close"].pct_change().rename(code)
        rets.append(r)
        valid_codes.append(code)

    if not rets:
        return pd.DataFrame()

    frame = pd.concat(rets, axis=1).dropna(how="all")
    if frame.empty:
        return frame

    # 等权组合收益 = 各标的当日收益率的均值（对齐后可计算）
    if method == "equal":
        frame["组合"] = frame.mean(axis=1)
    return frame


def portfolio_equity(codes: list[str], initial_cash: float = 1_000_000.0,
                     period: str = "day", fqt: str = "qfq",
                     beg: str = "0", method: str = "equal") -> pd.DataFrame:
    """组合净值曲线（等权，每日再平衡近似）"""
    rets = portfolio_returns(codes, period, fqt, beg, method)
    if rets.empty:
        return pd.DataFrame()
    if "组合" not in rets.columns:
        return pd.DataFrame()
    eq = initial_cash * (1 + rets["组合"].fillna(0)).cumprod()
    out = pd.DataFrame({
        "date": rets.index,
        "equity": eq,
        "ret": rets["组合"].fillna(0),
    })
    return out
