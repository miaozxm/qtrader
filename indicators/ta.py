"""常用技术指标计算（基于 pandas）"""
import numpy as np
import pandas as pd


def ma(series: pd.Series, n: int = 5) -> pd.Series:
    """简单移动平均"""
    return series.rolling(n, min_periods=1).mean()


def ema(series: pd.Series, n: int = 12) -> pd.Series:
    """指数移动平均"""
    return series.ewm(span=n, adjust=False).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD 指标，返回 (DIF, DEA, HIST)"""
    dif = ema(close, fast) - ema(close, slow)
    dea = ema(dif, signal)
    hist = 2 * (dif - dea)
    return dif, dea, hist


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """相对强弱指标 RSI"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.fillna(50.0)


def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
        n: int = 9, m1: int = 3, m2: int = 3):
    """随机指标 KDJ，返回 (K, D, J)"""
    low_n = low.rolling(n, min_periods=1).min()
    high_n = high.rolling(n, min_periods=1).max()
    rsv = (close - low_n) / (high_n - low_n).replace(0, np.nan) * 100
    rsv = rsv.fillna(50.0)
    k = rsv.ewm(alpha=1 / m1, adjust=False).mean()
    d = k.ewm(alpha=1 / m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def boll(close: pd.Series, n: int = 20, k: float = 2.0):
    """布林带，返回 (MID, UPPER, LOWER)"""
    mid = ma(close, n)
    std = close.rolling(n, min_periods=1).std()
    upper = mid + k * std
    lower = mid - k * std
    return mid, upper, lower


def add_indicators(df: pd.DataFrame,
                   mas: tuple = (5, 10, 20, 60),
                   macd_on: bool = True,
                   rsi_on: bool = True,
                   kdj_on: bool = True,
                   boll_on: bool = True) -> pd.DataFrame:
    """给K线DataFrame批量添加指标列，返回新DataFrame"""
    out = df.copy()
    close = out["close"]

    if mas:
        for n in mas:
            out[f"MA{n}"] = ma(close, n)

    if macd_on:
        dif, dea, hist = macd(close)
        out["DIF"] = dif
        out["DEA"] = dea
        out["MACD"] = hist

    if rsi_on:
        out["RSI"] = rsi(close)

    if kdj_on:
        k, d, j = kdj(out["high"], out["low"], close)
        out["K"] = k
        out["D"] = d
        out["J"] = j

    if boll_on:
        mid, up, lo = boll(close)
        out["BOLL_MID"] = mid
        out["BOLL_UP"] = up
        out["BOLL_LOW"] = lo

    return out
