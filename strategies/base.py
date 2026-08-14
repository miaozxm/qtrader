"""策略定义：输入K线，输出买卖信号"""
import abc

import numpy as np
import pandas as pd

from indicators.ta import add_indicators, ma, macd, rsi


class Strategy(abc.ABC):
    """策略基类

    子类实现 generate_signal(df) 返回带 'signal' 列的DataFrame：
        signal = 1 买入 / -1 卖出 / 0 持有
    """

    name = "策略"

    def __init__(self, **params):
        self.params = params

    @abc.abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        ...

    def __repr__(self):
        return f"{self.name}({self.params})"


class DualMAStrategy(Strategy):
    """双均线策略：快线上穿慢线买入，下穿卖出"""

    name = "双均线"

    def __init__(self, fast: int = 5, slow: int = 20, **kw):
        super().__init__(fast=fast, slow=slow, **kw)
        self.fast = fast
        self.slow = slow

    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["ma_fast"] = ma(out["close"], self.fast)
        out["ma_slow"] = ma(out["close"], self.slow)
        out["signal"] = 0
        out.loc[out["ma_fast"] > out["ma_slow"], "signal"] = 1
        out.loc[out["ma_fast"] < out["ma_slow"], "signal"] = -1
        return out


class MACDStrategy(Strategy):
    """MACD 金叉死叉策略：DIF上穿DEA买入，下穿卖出"""

    name = "MACD金叉"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9, **kw):
        super().__init__(fast=fast, slow=slow, signal=signal, **kw)
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        dif, dea, hist = macd(out["close"], self.fast, self.slow, self.signal)
        out["DIF"], out["DEA"], out["MACD"] = dif, dea, hist
        out["signal"] = 0
        # 金叉买入
        cross_up = (dif > dea) & (dif.shift(1) <= dea.shift(1))
        # 死叉卖出
        cross_down = (dif < dea) & (dif.shift(1) >= dea.shift(1))
        out.loc[cross_up, "signal"] = 1
        out.loc[cross_down, "signal"] = -1
        return out


class RSIStrategy(Strategy):
    """RSI 超买超卖策略：RSI < 30 买入，RSI > 70 卖出"""

    name = "RSI超买超卖"

    def __init__(self, n: int = 14, buy: float = 30, sell: float = 70, **kw):
        super().__init__(n=n, buy=buy, sell=sell, **kw)
        self.n = n
        self.buy = buy
        self.sell = sell

    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["RSI"] = rsi(out["close"], self.n)
        out["signal"] = 0
        out.loc[out["RSI"] < self.buy, "signal"] = 1
        out.loc[out["RSI"] > self.sell, "signal"] = -1
        return out


def signal_to_position(signal: pd.Series) -> pd.Series:
    """将信号序列转为持仓状态（多头1 / 空头0）：
    遇到1做多，遇到-1平仓，其余保持原状
    """
    pos = np.zeros(len(signal))
    cur = 0.0
    sig = signal.fillna(0).values
    for i, s in enumerate(sig):
        if s == 1:
            cur = 1.0
        elif s == -1:
            cur = 0.0
        pos[i] = cur
    return pd.Series(pos, index=signal.index)


# 已注册策略（用于界面下拉选择）
STRATEGY_REGISTRY = {
    "双均线": DualMAStrategy,
    "MACD金叉": MACDStrategy,
    "RSI超买超卖": RSIStrategy,
}
