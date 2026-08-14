"""测试 ETF / 基金代码的支持情况"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from data.fetcher import fetcher
from data.symbols import detect_market, to_secid


def main():
    etf_codes = [
        "510300",   # 沪深300ETF 沪
        "510050",   # 上证50ETF 沪
        "159915",   # 创业板ETF 深
        "513100",   # 纳指ETF 沪
        "518880",   # 黄金ETF 沪
        "512880",   # 证券ETF 沪
        "00700",    # 港股 腾讯
        "02800",    # 港股 盈富基金
        "09988",    # 港股 阿里
        "600519",   # A股 茅台
    ]
    for code in etf_codes:
        try:
            market = detect_market(code)
            secid = to_secid(code)
            df = fetcher.get_kline_by_code(code, period="day", beg="20240101")
            n = len(df)
            last = ""
            if not df.empty:
                last = f"最新 {df.iloc[-1]['date'].date()} 收盘 {df.iloc[-1]['close']}"
            print(f"{code}: market={market} secid={secid} bars={n} {last}")
        except Exception as e:
            print(f"{code}: ERROR {e}")


if __name__ == "__main__":
    main()
