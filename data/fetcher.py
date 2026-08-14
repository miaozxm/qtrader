"""行情数据获取：东方财富（主） + 腾讯（备用），自动降级"""
import time
import re

import pandas as pd
import requests

from config import HTTP_RETRIES, HTTP_TIMEOUT


class _BaseFetcher:
    """带重试、限流的请求基类"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._last_request_at = 0.0
        self._min_interval = 0.35

    def _throttle(self):
        elapsed = time.time() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_at = time.time()

    def _get(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        last_err = None
        for attempt in range(HTTP_RETRIES):
            try:
                self._throttle()
                resp = self.session.get(url, params=params, headers=headers,
                                        timeout=HTTP_TIMEOUT)
                resp.raise_for_status()
                return resp
            except Exception as e:
                last_err = e
                if attempt < HTTP_RETRIES - 1:
                    time.sleep(1.0 * (attempt + 1))
        raise ConnectionError(f"请求 {url} 失败：{last_err}") from last_err


class EastMoneyFetcher(_BaseFetcher):
    """东方财富数据源（免费、无需 token）：K线 / 实时 / 列表"""

    KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    REALTIME_URL = "https://push2.eastmoney.com/api/qt/stock/get"
    LIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    HEADERS = {
        **_BaseFetcher.HEADERS,
        "Referer": "https://quote.eastmoney.com/",
    }

    PERIOD_MAP = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30, "60m": 60,
        "day": 101, "week": 102, "month": 103,
    }
    FQT_MAP = {"qfq": 1, "hfq": 2, "none": 0}

    def get_kline(self, secid: str, period: str = "day", fqt: str = "qfq",
                  beg: str = "0", end: str = "20500101") -> pd.DataFrame:
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": self.PERIOD_MAP.get(period, 101),
            "fqt": self.FQT_MAP.get(fqt, 1),
            "beg": beg, "end": end, "lmt": 1000000,
        }
        data = self._get(self.KLINE_URL, params).json().get("data") or {}
        klines = data.get("klines") or []
        return self._parse_em_kline(klines)

    @staticmethod
    def _parse_em_kline(klines) -> pd.DataFrame:
        if not klines:
            return pd.DataFrame()
        rows = []
        for k in klines:
            p = k.split(",")
            rows.append({
                "date": p[0], "open": float(p[1]), "close": float(p[2]),
                "high": float(p[3]), "low": float(p[4]),
                "volume": float(p[5]), "amount": float(p[6]),
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        return df

    def get_realtime(self, secid: str) -> dict:
        params = {
            "secid": secid, "fltt": 2, "invt": 2,
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f107,f168,f116,f117,f162,f167",
        }
        data = self._get(self.REALTIME_URL, params).json().get("data") or {}
        if not data:
            return {}
        return {
            "source": "eastmoney",
            "code": data.get("f57"), "name": data.get("f58"),
            "price": data.get("f43"), "high": data.get("f44"),
            "low": data.get("f45"), "open": data.get("f46"),
            "volume": data.get("f47"), "amount": data.get("f48"),
            "prev_close": data.get("f60"), "market": data.get("f107"),
            "turnover": data.get("f168"), "pe": data.get("f162"),
            "pb": data.get("f167"),
        }

    def get_stock_list(self, market: str = "A股", limit: int = 50,
                       sort_field: str = "f3", sort_desc: bool = True) -> pd.DataFrame:
        fs_map = {
            "A股": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "港股": "m:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2",
        }
        params = {
            "pn": 1, "pz": min(limit, 200), "po": 1 if sort_desc else 0,
            "np": 1, "fltt": 2, "invt": 2, "fid": sort_field,
            "fs": fs_map.get(market, fs_map["A股"]),
            "fields": "f2,f3,f4,f5,f6,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21",
        }
        data = self._get(self.LIST_URL, params).json().get("data") or {}
        diff = data.get("diff") or []
        if not diff:
            return pd.DataFrame()
        rows = [{
            "code": d.get("f12"), "name": d.get("f14"), "price": d.get("f2"),
            "pct_chg": d.get("f3"), "chg": d.get("f4"),
            "volume": d.get("f5"), "amount": d.get("f6"),
            "turnover": d.get("f8"), "pe": d.get("f9"),
            "volume_ratio": d.get("f10"), "high": d.get("f15"),
            "low": d.get("f16"), "open": d.get("f17"),
            "prev_close": d.get("f18"),
            "total_mv": d.get("f20"), "float_mv": d.get("f21"),
        } for d in diff]
        return pd.DataFrame(rows)


class TencentFetcher(_BaseFetcher):
    """腾讯数据源（备用）：K线 / 实时行情"""

    KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    REALTIME_URL = "https://qt.gtimg.cn/q="
    HEADERS = {
        **_BaseFetcher.HEADERS,
        "Referer": "https://gu.qq.com/",
    }

    PERIOD_MAP = {
        "1m": "m1", "5m": "m5", "15m": "m15", "30m": "m30", "60m": "m60",
        "day": "day", "week": "week", "month": "month",
    }

    @staticmethod
    def to_tx_symbol(code: str) -> str:
        """转腾讯 symbol：sh600519 / sz000001 / hk00700"""
        from data.symbols import detect_market
        market = detect_market(code)
        if market == "港股":
            return f"hk{code}"
        return f"sh{code}" if code.startswith(("6", "5")) else f"sz{code}"

    def get_kline(self, code: str, period: str = "day", fqt: str = "qfq",
                  beg: str = "0", end: str = "20500101") -> pd.DataFrame:
        """腾讯K线

        Note: 腾讯接口用起始日期+条数，这里先拉全量再截取 beg 之后
        """
        symbol = self.to_tx_symbol(code)
        tx_period = self.PERIOD_MAP.get(period, "day")
        # 腾讯 count 上限约 800，日K取800根足够最近3年
        params = {
            "param": f"{symbol},{tx_period},1990-01-01,2030-12-31,800,"
                     f"{'qfq' if fqt == 'qfq' else ('hfq' if fqt == 'hfq' else '')}",
        }
        data = self._get(self.KLINE_URL, params).json()
        node = (data.get("data") or {}).get(symbol) or {}
        # 腾讯返回键名：qfqday / hfqday / day / qfqweek ...
        key = f"{fqt}{tx_period}" if fqt != "none" else tx_period
        klines = node.get(key) or node.get(tx_period) or []
        df = self._parse_tx_kline(klines)
        if beg and beg != "0" and not df.empty:
            df = df[df["date"] >= pd.to_datetime(beg)]
        return df.reset_index(drop=True)

    @staticmethod
    def _parse_tx_kline(klines) -> pd.DataFrame:
        if not klines:
            return pd.DataFrame()
        rows = []
        for p in klines:
            if len(p) < 6:
                continue
            amount = 0.0
            if len(p) > 6 and isinstance(p[6], str):
                try:
                    amount = float(p[6])
                except ValueError:
                    amount = 0.0
            rows.append({
                "date": p[0], "open": float(p[1]), "close": float(p[2]),
                "high": float(p[3]), "low": float(p[4]), "volume": float(p[5]),
                "amount": amount,
            })
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        return df

    def get_realtime(self, code: str) -> dict:
        symbol = self.to_tx_symbol(code)
        resp = self._get(self.REALTIME_URL + symbol).text
        m = re.search(r'="([^"]*)"', resp)
        if not m:
            return {}
        parts = m.group(1).split("~")
        if len(parts) < 45:
            return {}

        def _f(idx, default=0.0):
            try:
                return float(parts[idx]) if parts[idx] not in ("", "-") else default
            except (ValueError, IndexError):
                return default

        return {
            "source": "tencent",
            "code": parts[2], "name": parts[1],
            "price": _f(3), "prev_close": _f(4), "open": _f(5),
            "volume": _f(6), "high": _f(33), "low": _f(34),
            "amount": _f(37) * 10000,          # 腾讯成交额单位：万元
            "turnover": _f(38), "pe": _f(39), "pb": _f(46),
            "market": None,
        }


class DataFetcher:
    """统一数据获取门面：东方财富优先，失败自动降级腾讯"""

    def __init__(self):
        self.em = EastMoneyFetcher()
        self.tx = TencentFetcher()
        self._last_fail = {}   # 记录各接口最近失败源，用于快速切换

    def get_kline(self, secid: str, period: str = "day", fqt: str = "qfq",
                  beg: str = "0", end: str = "20500101") -> pd.DataFrame:
        """按 secid 获取K线，返回带 date/open/high/low/close/volume/amount"""
        # 从 secid 还原代码
        from data.symbols import code_from_secid
        code = code_from_secid(secid)
        try:
            df = self.em.get_kline(secid, period, fqt, beg, end)
            if not df.empty:
                return df
        except Exception:
            pass
        # 降级腾讯
        try:
            df = self.tx.get_kline(code, period, fqt, beg, end)
            return df
        except Exception as e:
            raise ConnectionError(f"东财与腾讯均获取K线失败：{e}") from e

    def get_kline_by_code(self, code: str, market: str | None = None,
                          period: str = "day", fqt: str = "qfq",
                          beg: str = "0", end: str = "20500101") -> pd.DataFrame:
        from data.symbols import to_secid
        return self.get_kline(to_secid(code), period, fqt, beg, end)

    def get_realtime(self, secid: str) -> dict:
        from data.symbols import code_from_secid
        code = code_from_secid(secid)
        try:
            rt = self.em.get_realtime(secid)
            if rt.get("price") is not None:
                return rt
        except Exception:
            pass
        try:
            return self.tx.get_realtime(code)
        except Exception as e:
            raise ConnectionError(f"东财与腾讯均获取实时行情失败：{e}") from e

    def get_realtime_by_code(self, code: str) -> dict:
        from data.symbols import to_secid
        return self.get_realtime(to_secid(code))

    def get_stock_list(self, market: str = "A股", limit: int = 50,
                       sort_field: str = "f3", sort_desc: bool = True) -> pd.DataFrame:
        """榜单：目前仅东财提供，失败返回空表"""
        try:
            return self.em.get_stock_list(market, limit, sort_field, sort_desc)
        except Exception:
            return pd.DataFrame()


# 模块级单例
fetcher = DataFetcher()
