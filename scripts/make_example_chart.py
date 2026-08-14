"""生成示例 K线图（PNG），用于快速预览效果"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd

from data.fetcher import fetcher
from data.storage import storage
from data.symbols import to_secid
from indicators.ta import add_indicators
from strategies.base import MACDStrategy


def _setup_chinese_font():
    """设置中文字体（Windows 用微软雅黑）"""
    from matplotlib import font_manager
    for font in ("Microsoft YaHei", "SimHei", "SimSun"):
        try:
            font_manager.findfont(font, fallback_to_default=False)
            plt.rcParams["font.sans-serif"] = [font]
            break
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False


def main():
    _setup_chinese_font()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "example_kline.png")

    # 获取贵州茅台日K（优先缓存）
    code = "600519"
    df = storage.load_bars(to_secid(code), "day", "qfq")
    if df.empty:
        df = fetcher.get_kline_by_code(code, period="day", beg="20250101")
        storage.save_bars(to_secid(code), "day", "qfq", df)
    if df.empty:
        print("数据获取失败")
        sys.exit(1)

    dfi = add_indicators(df)
    strat = MACDStrategy()
    sig = strat.generate_signal(dfi)
    sig["date"] = pd.to_datetime(sig["date"])
    sig = sig.set_index("date")

    # 买卖点（需全长度数组，买点处填价格，其余 NaN）
    n = len(sig)
    buy_y = pd.Series(np.nan, index=sig.index)
    sell_y = pd.Series(np.nan, index=sig.index)
    buy_y[sig["signal"] > 0] = sig["close"][sig["signal"] > 0]
    sell_y[sig["signal"] < 0] = sig["close"][sig["signal"] < 0]

    apds = [
        mpf.make_addplot(sig["MA5"], color="#f39c12", width=0.8),
        mpf.make_addplot(sig["MA20"], color="#3498db", width=0.8),
        mpf.make_addplot(buy_y, type="scatter", marker="^",
                         markersize=90, color="#e74c3c", panel=0),
        mpf.make_addplot(sell_y, type="scatter", marker="v",
                         markersize=90, color="#2ecc71", panel=0),
    ]
    mpf.plot(
        sig[["open", "high", "low", "close", "volume"]],
        type="candle", style="yahoo", addplot=apds,
        volume=True, mav=(5, 20), title=f"贵州茅台 600519 日K + MACD策略",
        savefig=out_path, figsize=(14, 8), tight_layout=True,
    )
    print(f"示例图已保存: {out_path}")


if __name__ == "__main__":
    main()
