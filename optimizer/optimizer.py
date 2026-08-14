"""策略参数网格寻优"""
from itertools import product

import pandas as pd

from backtest.engine import BacktestEngine, format_metrics
from data.storage import storage
from data.fetcher import fetcher
from data.symbols import to_secid
from indicators.ta import add_indicators
from strategies.base import DualMAStrategy, MACDStrategy, RSIStrategy


# 各策略的参数网格定义
PARAM_GRIDS = {
    "双均线": {
        "fast": [3, 5, 8, 10, 13],
        "slow": [20, 30, 40, 55, 60],
    },
    "MACD金叉": {
        "fast": [8, 12, 16],
        "slow": [20, 26, 30],
        "signal": [7, 9, 12],
    },
    "RSI超买超卖": {
        "n": [6, 9, 14, 21],
        "buy": [20, 25, 30, 35],
        "sell": [65, 70, 75, 80],
    },
}

STRATEGY_FACTORY = {
    "双均线": DualMAStrategy,
    "MACD金叉": MACDStrategy,
    "RSI超买超卖": RSIStrategy,
}


def get_data_cached(code: str, period: str = "day", fqt: str = "qfq",
                    beg: str = "0") -> pd.DataFrame:
    """获取K线（优先缓存），供寻优使用"""
    secid = to_secid(code)
    df = storage.load_bars(secid, period, fqt)
    if df.empty:
        df = fetcher.get_kline(secid, period, fqt, beg=beg)
        if not df.empty:
            storage.save_bars(secid, period, fqt, df)
    return df


def optimize(code: str, strategy_name: str,
             param_grid: dict | None = None,
             period: str = "day", fqt: str = "qfq", beg: str = "0",
             metric: str = "年化收益", top_n: int = 10,
             initial_cash: float = 100_000.0, progress=None) -> pd.DataFrame:
    """网格寻优

    Args:
        code: 股票代码
        strategy_name: 策略名（PARAM_GRIDS 中的键）
        param_grid: 自定义参数网格，默认使用内置
        metric: 寻优排序指标（总收益率/年化收益/最大回撤/夏普比率）
        top_n: 返回最优前 N 组
        progress: 可选回调 (done, total)

    Returns:
        DataFrame：参数列 + 绩效指标列，按 metric 降序
    """
    if strategy_name not in STRATEGY_FACTORY:
        raise ValueError(f"未知策略: {strategy_name}")

    grid = param_grid or PARAM_GRIDS.get(strategy_name, {})
    if not grid:
        raise ValueError(f"策略 {strategy_name} 未配置参数网格")

    df = get_data_cached(code, period, fqt, beg)
    if df.empty or len(df) < 100:
        raise ValueError(f"数据不足: {code} 仅 {len(df)} 根K线")
    dfi = add_indicators(df)

    keys = list(grid.keys())
    combos = list(product(*[grid[k] for k in keys]))
    total = len(combos)

    results = []
    engine = BacktestEngine(initial_cash=initial_cash)
    for i, combo in enumerate(combos, start=1):
        params = dict(zip(keys, combo))
        strat_cls = STRATEGY_FACTORY[strategy_name]
        # 过滤无效参数（fast >= slow 时跳过）
        if strategy_name == "双均线" and params["fast"] >= params["slow"]:
            continue
        if strategy_name == "MACD金叉" and params["fast"] >= params["slow"]:
            continue

        try:
            strat = strat_cls(**params)
            signal_df = strat.generate_signal(dfi)
            res = engine.run(signal_df)
            m = res["metrics"]
            results.append({
                **params,
                "总收益率": m.get("总收益率", 0),
                "年化收益": m.get("年化收益", 0),
                "最大回撤": m.get("最大回撤", 0),
                "夏普比率": m.get("夏普比率", 0),
                "交易次数": m.get("交易次数", 0),
                "胜率": m.get("胜率", 0),
                "期末资产": m.get("期末资产", 0),
            })
        except Exception:
            pass
        if progress:
            progress(i, total)

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results)
    if metric in out.columns:
        out = out.sort_values(metric, ascending=False)
    return out.head(top_n).reset_index(drop=True)
