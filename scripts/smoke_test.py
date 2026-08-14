"""端到端冒烟测试：数据 -> 指标 -> 策略 -> 回测"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtest.engine import BacktestEngine, format_metrics
from data.fetcher import fetcher
from data.storage import storage
from data.symbols import to_secid
from indicators.ta import add_indicators
from strategies.base import STRATEGY_REGISTRY


def main():
    # 1) A股日K（优先缓存）
    df = storage.load_bars(to_secid("600519"), "day", "qfq")
    if df.empty:
        df = fetcher.get_kline_by_code("600519", period="day", beg="20240101")
        storage.save_bars(to_secid("600519"), "day", "qfq", df)
    print("A股贵州茅台 bars:", len(df))

    # 2) 指标
    dfi = add_indicators(df)
    new_cols = [c for c in dfi.columns if c not in df.columns]
    print("新增指标列:", new_cols)

    # 3) 每个策略回测
    for name, cls in STRATEGY_REGISTRY.items():
        strat = cls()
        sig = strat.generate_signal(dfi)
        result = BacktestEngine().run(sig)
        m = result["metrics"]
        win = f"{m['胜率']*100:.1f}%" if m["胜率"] == m["胜率"] else "N/A"
        print(f"\n=== {name} === 交易:{m['交易次数']} 胜率:{win} "
              f"期末:{m['期末资产']:.0f}")
        keys = ["总收益率", "年化收益", "最大回撤", "夏普比率"]
        print("  ", {k: format_metrics(m)[k] for k in keys})
        print("  交易明细示例:")
        if not result["trades"].empty:
            print("   ", result["trades"].head(4).to_string(index=False))

    # 4) 港股K线验证
    dfh = fetcher.get_kline_by_code("00700", period="day", fqt="qfq", beg="20240101")
    print("\n港股腾讯 bars:", len(dfh), "最新:", dfh.iloc[-1]["date"].date())


if __name__ == "__main__":
    main()
