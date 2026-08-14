"""向量化回测引擎"""
import numpy as np
import pandas as pd

from config import DEFAULT_COMMISSION, DEFAULT_SLIPPAGE, DEFAULT_STAMP_TAX
from strategies.base import signal_to_position


class BacktestEngine:
    """基于K线的向量化回测引擎

    支持：
    - 多头策略（默认）
    - 手续费 / 印花税 / 滑点
    - 输出：净值曲线、交易明细、绩效指标
    """

    def __init__(self, commission=DEFAULT_COMMISSION, stamp_tax=DEFAULT_STAMP_TAX,
                 slippage=DEFAULT_SLIPPAGE, initial_cash=100_000.0):
        self.commission = commission
        self.stamp_tax = stamp_tax
        self.slippage = slippage
        self.initial_cash = initial_cash

    def run(self, df: pd.DataFrame, signal_col: str = "signal") -> dict:
        """运行回测

        Args:
            df: 含 open/high/low/close 和 signal 列的K线

        Returns:
            {
                "equity": DataFrame(净值曲线),
                "trades": DataFrame(交易明细),
                "metrics": dict(绩效指标),
                "signals": DataFrame(带信号的K线)
            }
        """
        data = df.copy()
        data["position"] = signal_to_position(data.get(signal_col, pd.Series(0, index=data.index)))

        close = data["close"]
        # 持仓变化（相对昨日）
        pos_shift = data["position"].shift(1).fillna(0)
        turnover = (data["position"] - pos_shift).abs()

        # 次日价格变化带来的收益（T+1：当天信号次日执行）
        ret = close.pct_change().fillna(0)
        strategy_ret = data["position"].shift(1).fillna(0) * ret

        # 交易成本 = 手续费 + 印花税(卖出) + 滑点
        buy_turn = turnover.where(data["position"] > pos_shift, 0.0)
        sell_turn = turnover.where(data["position"] < pos_shift, 0.0)
        cost = (
            turnover * self.commission
            + sell_turn * self.stamp_tax
            + turnover * self.slippage
        )
        net_ret = strategy_ret - cost

        equity = self.initial_cash * (1 + net_ret).cumprod()
        equity_df = pd.DataFrame({
            "date": data["date"],
            "close": close,
            "position": data["position"],
            "strategy_ret": strategy_ret,
            "net_ret": net_ret,
            "equity": equity,
        })

        # 基准（买入持有）
        bench_ret = (close / close.iloc[0] - 1) * self.initial_cash + self.initial_cash
        equity_df["benchmark"] = bench_ret

        trades = self._build_trades(data, equity_df)
        metrics = self._calc_metrics(equity_df, data, trades)

        return {
            "equity": equity_df,
            "trades": trades,
            "metrics": metrics,
            "signals": data,
        }

    def _build_trades(self, data: pd.DataFrame, equity_df: pd.DataFrame) -> pd.DataFrame:
        """从持仓变化提取交易明细"""
        pos = data["position"]
        pos_shift = pos.shift(1).fillna(0)
        change = pos - pos_shift
        idx = data.index[change != 0]

        trades = []
        for i in idx:
            side = "买入" if change.loc[i] > 0 else "卖出"
            trades.append({
                "date": data.loc[i, "date"],
                "side": side,
                "price": data.loc[i, "close"],
                "position": pos.loc[i],
            })
        return pd.DataFrame(trades)

    def _calc_metrics(self, equity_df: pd.DataFrame, data: pd.DataFrame,
                      trades: pd.DataFrame) -> dict:
        """计算绩效指标"""
        eq = equity_df["equity"].values
        n = len(eq)
        if n < 2:
            return {}

        ret_series = equity_df["net_ret"]
        total_ret = eq[-1] / self.initial_cash - 1

        # 年化（按日，约252交易日）
        years = max(n / 252, 1e-9)
        annual_ret = (eq[-1] / self.initial_cash) ** (1 / years) - 1

        # 最大回撤
        cum_max = np.maximum.accumulate(eq)
        drawdown = eq / cum_max - 1
        max_dd = drawdown.min()

        # 夏普比率（无风险利率0）
        std = ret_series.std()
        sharpe = (annual_ret * 252 / (std * np.sqrt(252) + 1e-9)) if std > 0 else 0
        sharpe = (ret_series.mean() / (ret_series.std() + 1e-9)) * np.sqrt(252)

        # 胜率
        win_rate = None
        if len(trades) > 1:
            win = 0
            buys = trades[trades["side"] == "买入"]
            sells = trades[trades["side"] == "卖出"]
            for _, b in buys.iterrows():
                later_sells = sells[sells["date"] > b["date"]]
                if not later_sells.empty:
                    s = later_sells.iloc[0]
                    if s["price"] > b["price"]:
                        win += 1
            win_rate = win / max(len(buys), 1)

        return {
            "总收益率": total_ret,
            "年化收益": annual_ret,
            "最大回撤": max_dd,
            "夏普比率": sharpe,
            "交易次数": len(trades),
            "胜率": win_rate if win_rate is not None else float("nan"),
            "期末资产": eq[-1],
            "初始资金": self.initial_cash,
            "交易日数": n,
        }


def format_metrics(metrics: dict) -> dict:
    """格式化指标为可读字符串"""
    fmt = {
        "总收益率": lambda v: f"{v * 100:.2f}%",
        "年化收益": lambda v: f"{v * 100:.2f}%",
        "最大回撤": lambda v: f"{v * 100:.2f}%",
        "夏普比率": lambda v: f"{v:.2f}",
        "交易次数": lambda v: f"{v}",
        "胜率": lambda v: f"{v * 100:.1f}%" if v == v else "N/A",
        "期末资产": lambda v: f"{v:,.2f}",
        "初始资金": lambda v: f"{v:,.2f}",
        "交易日数": lambda v: f"{v}",
    }
    return {k: fmt.get(k, str)(v) for k, v in metrics.items()}
