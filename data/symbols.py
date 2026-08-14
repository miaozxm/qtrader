"""股票代码解析：判断市场、生成东财 secid"""
import re

from config import MARKETS


def detect_market(code: str) -> str:
    """根据代码判断市场（A股 / 港股）

    - 6 开头：沪市主板/科创板
    - 0、3 开头：深市主板/创业板
    - 5 开头：沪市基金/ETF
    - 4、8 开头：北交所/新三板（暂归 A股）
    - 其它 4-5 位纯数字：港股
    """
    code = code.strip().upper()
    if code.startswith(("6", "0", "3", "5", "4", "8")) and len(code) == 6:
        return "A股"
    if re.fullmatch(r"\d{4,5}", code):
        return "港股"
    raise ValueError(f"无法识别的股票代码: {code}")


def to_secid(code: str) -> str:
    """转成东方财富 secid

    A股：上海 = 1.XXXXXX，深圳 = 0.XXXXXX
    港股：116.XXXXX
    """
    market = detect_market(code)
    code = code.strip()
    if market == "港股":
        return f"116.{code}"
    # A股：沪市 1，深市 0
    prefix = "1" if code.startswith(("6", "5")) else "0"
    return f"{prefix}.{code}"


def code_from_secid(secid: str) -> str:
    """从东财 secid 还原纯代码（1.600519 -> 600519，116.00700 -> 00700）"""
    return secid.split(".")[1] if "." in secid else secid


def normalize_code(code: str) -> str:
    """统一代码格式（返回去除点号后的纯代码）"""
    return code.strip().upper().replace(".", "").replace("-", "")


def is_index(code: str) -> bool:
    """是否指数代码（上证/深证指数）"""
    return code in {"000001", "399001", "399006", "000300", "000905", "000016", "000688"}
