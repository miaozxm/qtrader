"""组合监控功能测试"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from data.fetcher import fetcher
from portfolio.portfolio import portfolio_equity, portfolio_returns
from portfolio.watchlist import watchlist


def main():
    # 1) 自选股管理
    watchlist.clear()
    for code, name in [("600519", "贵州茅台"), ("000001", "平安银行"),
                       ("688981", "中芯国际"), ("00700", "腾讯控股")]:
        print(f"添加 {code}:", watchlist.add(code, name))
    items = watchlist.get_all()
    print("自选列表:", [(i["code"], i["name"]) for i in items])
    print("包含 600519:", watchlist.contains("600519"))

    # 2) 组合收益率
    codes = [i["code"] for i in items]
    rets = portfolio_returns(codes, beg="20250101")
    print("\n组合收益矩阵 shape:", rets.shape)
    if not rets.empty:
        print("组合列头:", list(rets.columns))
        print("最新一天组合收益:", round(float(rets["组合"].iloc[-1]), 6))

    # 3) 组合净值
    eq = portfolio_equity(codes, initial_cash=1_000_000, beg="20250101")
    print("\n组合净值曲线点数:", len(eq))
    if not eq.empty:
        total = (eq["equity"].iloc[-1] / 1_000_000 - 1) * 100
        print(f"组合总收益: {total:.2f}%  期末净值: {eq['equity'].iloc[-1]:,.0f}")

    # 4) 清理测试数据
    watchlist.clear()
    print("\n测试完成，已清理自选数据")


if __name__ == "__main__":
    main()
