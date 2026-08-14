"""验证选股条件函数的正确性"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from data.fetcher import fetcher
from indicators.ta import add_indicators
from screener.screener import CONDITIONS


def main():
    for code in ["600519", "000001", "688981", "300750"]:
        df = fetcher.get_kline_by_code(code, period="day", beg="20250101")
        if df.empty or len(df) < 70:
            print(code, "数据不足")
            continue
        dfi = add_indicators(df)
        last = dfi.iloc[-1]
        print(f"{code} MA5={last['MA5']:.2f} MA10={last['MA10']:.2f} "
              f"MA20={last['MA20']:.2f} MA60={last['MA60']:.2f} "
              f"RSI={last.get('RSI', 0):.1f}")
        for name, fn in CONDITIONS.items():
            try:
                print(f"   {name}: {bool(fn(dfi))}")
            except Exception as e:
                print(f"   {name}: ERROR {e}")


if __name__ == "__main__":
    main()
