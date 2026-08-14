"""全局配置"""
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 数据缓存目录
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# SQLite 缓存数据库
DB_PATH = CACHE_DIR / "qtrader.db"

# 请求超时（秒）
HTTP_TIMEOUT = 10

# 请求重试次数
HTTP_RETRIES = 3

# 回测默认参数
DEFAULT_COMMISSION = 0.0003     # 单边手续费（万3）
DEFAULT_STAMP_TAX = 0.0005      # 卖出印花税（万5，A股，港股约0.1%）
DEFAULT_SLIPPAGE = 0.0005       # 滑点（万5）

# 支持的市场
MARKETS = {
    "A股": {"name": "A股", "secid_market": "auto"},
    "港股": {"name": "港股", "secid_market": "116"},
}

# 交易时间（用于提示，非强校验）
TRADING_SESSION = {
    "A股": [("09:30", "11:30"), ("13:00", "15:00")],
    "港股": [("09:30", "12:00"), ("13:00", "16:00")],
}
