# QTrader — 个人量化交易平台

一个开箱即用的个人量化交易平台（MVP），重点：**数据获取简单、可视化轻松**。

> 🚧 **版本：V0.1（MVP）** —— 已可看行情、跑策略回测

## 已支持

- **A股 + 港股**：东方财富免费接口（主） + 腾讯接口（备用，自动降级）
- 实时行情、历史日K/周K/月K/分钟K、全市场股票列表
- 本地 **SQLite 缓存**，重复请求零延迟
- 常用技术指标：MA / EMA / MACD / RSI / KDJ / BOLL
- 自研**向量化回测引擎**（支持手续费、印花税、滑点）
- 内置策略：双均线、MACD金叉、RSI超买超卖
- **Streamlit + Plotly** 交互可视化：K线、指标副图、买卖点、回测净值曲线、交易明细

## 快速开始

**方式一（推荐）：双击 `启动平台.bat`**

**方式二（命令行）：**
```bash
cd qtrader
rem 首次使用先创建并配置项目虚拟环境（保证依赖自包含，避免系统 Python 混乱）
.venv\Scripts\python.exe -m pip install -r requirements.txt
python run.py
```

浏览器打开 `http://localhost:8501` 即可。

> 💡 **关于虚拟环境**：平台自带 `.venv`（项目本地 Python 环境），启动脚本会优先使用它。
> 这是为了避免你机器上多个 Python（VeighNa Studio / Anaconda / Miniconda）互相干扰，
> 尤其是解决 "ModuleNotFoundError: No module named 'plotly'" 这类环境串用问题。

## 目录结构

```
qtrader/
├── 启动平台.bat        # Windows 一键启动
├── run.py              # 启动入口
├── app/app.py          # Streamlit 可视化界面
├── data/
│   ├── fetcher.py      # 数据获取（东方财富 + 腾讯自动切换）
│   ├── storage.py      # SQLite 本地缓存
│   └── symbols.py      # 股票代码解析（A股/港股 secid）
├── indicators/ta.py    # 技术指标
├── strategies/base.py  # 策略定义（内置双均线/MACD/RSI）
├── backtest/engine.py  # 向量化回测引擎
├── scripts/            # 测试与工具脚本
│   ├── smoke_test.py           # 端到端冒烟测试（数据→指标→策略→回测）
│   ├── app_test.py             # Web 界面渲染测试（AppTest）
│   ├── app_interact_test.py    # 交互链路测试（查询+回测）
│   └── make_example_chart.py   # 生成示例K线图 PNG
├── config.py           # 全局配置
└── requirements.txt
```

## 代码约定

- A股代码：`600519`（沪）`000001`（深）
- 港股代码：`00700`（腾讯控股，5位）
- 统一 DataFrame 列：`date open high low close volume amount`
- 数据源自动降级：东财失败时自动切换腾讯，无需干预

## 已验证

- 数据：A股 5549 只、港股 4679 只列表；日K/实时行情均可获取
- 回测：3 个内置策略在贵州茅台/腾讯控股上均跑通，输出净值/回撤/夏普等指标
- 界面：AppTest 模拟查询港股 + 运行回测，无异常

## 路线图（Roadmap）

- [x] **V0.1 MVP**：行情数据（A股/港股）、K线可视化、指标、单标的回测
- [ ] **V0.2 选股器**：全市场策略扫描（双均线/MACD/RSI 选股），一键生成候选池
- [ ] **V0.3 组合监控**：自选股管理、多标的回测与组合净值、策略信号面板
- [ ] **V0.4 策略实验室**：参数寻优（grid search）、多周期多市场扩展
- [ ] **V0.5 实盘/模拟盘**：对接 vn.py 生态（vnpy_ctp / vnpy_xtp）交易接口

## 技术栈

- **数据**：东方财富 + 腾讯（免费公开接口，自动降级）
- **存储**：SQLite 本地缓存
- **可视化**：Streamlit + Plotly（交互式 K线 / 指标 / 净值曲线）
- **回测**：自研向量化回测引擎（手续费/印花税/滑点）
- **环境**：项目自带 `.venv` 虚拟环境，依赖自包含
