"""QTrader 可视化平台（Streamlit + Plotly）

运行：
    streamlit run app/app.py
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# 让项目根目录可导入
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backtest.engine import BacktestEngine, format_metrics
from data.fetcher import fetcher
from data.storage import storage
from data.symbols import to_secid
from indicators.ta import add_indicators
from optimizer.optimizer import PARAM_GRIDS, STRATEGY_FACTORY, optimize
from paper.account import paper_account
from portfolio.portfolio import portfolio_equity, portfolio_returns
from portfolio.watchlist import watchlist
from screener.screener import CONDITIONS, Screener
from strategies.base import STRATEGY_REGISTRY


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# 页面基础：品牌 + 全局样式
# ----------------------------------------------------------------------
st.set_page_config(page_title="QTrader 量化平台", layout="wide",
                   page_icon="📈")

# ---- 全局设计语言（CSS） ----
st.markdown("""
<style>
    :root {
        --brand: #2563eb;
        --brand-dark: #1d4ed8;
        --ink: #0f172a;
        --muted: #64748b;
        --line: #e2e8f0;
        --bg: #f8fafc;
        --card: #ffffff;
        --up: #dc2626;
        --down: #16a34a;
    }
    .stApp { background: var(--bg); }
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 1.6rem; }
    .block-container { padding-top: 2.4rem; padding-bottom: 4rem; }

    /* 品牌栏 */
    .qtrader-brand {
        display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
        margin-bottom: 6px;
    }
    .qtrader-brand .logo {
        font-size: 1.7rem; line-height: 1;
    }
    .qtrader-brand .name {
        font-size: 1.65rem; font-weight: 700; letter-spacing: -0.02em;
        color: var(--ink);
    }
    .qtrader-brand .name em {
        font-style: normal; color: var(--brand);
    }
    .qtrader-sub {
        color: var(--muted); font-size: 0.9rem; line-height: 1.5;
        margin-bottom: 1rem;
    }
    .qtrader-status {
        display: inline-flex; align-items: center; gap: 6px;
        background: #ecfdf5; color: #059669; font-size: 0.8rem;
        padding: 2px 10px; border-radius: 999px; margin-left: 8px;
    }
    .qtrader-status::before {
        content: ""; width: 6px; height: 6px; border-radius: 50%;
        background: #10b981; display: inline-block;
    }

    /* 功能卡片 */
    .qtrader-card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1.3rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04);
        transition: box-shadow .15s ease, transform .15s ease;
    }
    .qtrader-card:hover {
        box-shadow: 0 8px 24px rgba(15,23,42,0.08);
        transform: translateY(-1px);
    }
    .qtrader-card .card-ico { font-size: 1.6rem; }
    .qtrader-card .card-title {
        font-size: 1.08rem; font-weight: 650; color: var(--ink);
        margin: 8px 0 6px;
    }
    .qtrader-card .card-desc {
        color: var(--muted); font-size: 0.88rem; line-height: 1.6;
    }

    /* 按钮 */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: 1px solid var(--line);
        transition: all .15s ease;
    }
    .stButton > button[kind="primary"] {
        background: var(--brand);
        border: none;
        box-shadow: 0 2px 8px rgba(37,99,235,0.25);
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--brand-dark);
        box-shadow: 0 4px 14px rgba(37,99,235,0.35);
    }

    h1, h2, h3 { letter-spacing: -0.02em; color: var(--ink); }
    h3 { font-size: 1.12rem; font-weight: 650; }

    /* tabs 收敛 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; border-bottom: 1px solid var(--line);
        margin-bottom: 1.4rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9px 9px 0 0;
        padding: 8px 18px;
        font-size: 0.98rem;
        white-space: nowrap;
    }

    .stExpander {
        border: 1px solid var(--line) !important;
        border-radius: 12px !important;
        background: var(--card);
    }
    hr { border-color: var(--line) !important; }
</style>
""", unsafe_allow_html=True)

# ---- 品牌栏（紧凑） ----
st.markdown(
    '<div class="qtrader-brand">'
    '<span class="logo">📈</span>'
    '<span class="name">QTrader<em>·量化</em></span>'
    '</div>'
    '<div class="qtrader-sub">A股 / 港股 · 东方财富 + 腾讯数据源 · 本地缓存 · 个人量化研究平台</div>',
    unsafe_allow_html=True,
)


# 侧边栏：行情设置
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="qtrader-sub" style="margin-bottom:4px;">🔧 行情设置</div>',
        unsafe_allow_html=True,
    )
    market = st.selectbox("市场", ["A股", "港股"])

    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "周期",
            ["day", "week", "month", "60m", "30m", "15m", "5m", "1m"],
            format_func=lambda x: {
                "day": "日K", "week": "周K", "month": "月K",
                "60m": "60分钟", "30m": "30分钟", "15m": "15分钟",
                "5m": "5分钟", "1m": "1分钟",
            }[x],
        )
    with col2:
        fqt = st.selectbox(
            "复权",
            ["qfq", "hfq", "none"],
            format_func=lambda x: {"qfq": "前复权", "hfq": "后复权", "none": "不复权"}[x],
        )

    # 股票输入
    code = st.text_input(
        "股票代码",
        value="600519" if market == "A股" else "00700",
        help="A股：600519/000001；港股：00700（5位）",
    ).strip()

    if st.button("🔍 查询行情", type="primary", width="stretch"):
        st.session_state["code"] = code
        st.session_state["reload"] = True

    st.divider()
    st.header("热榜")
    rank_field = st.selectbox(
        "排行类型",
        ["f3", "f6", "f20", "f12", "f14"],
        format_func=lambda x: {
            "f3": "涨跌幅", "f6": "成交额", "f20": "总市值",
            "f12": "代码", "f14": "名称",
        }[x],
    )
    rank_n = st.slider("显示条数", 5, 50, 10, step=5)

# ----------------------------------------------------------------------
# 顶部指标卡片（实时行情）
# ----------------------------------------------------------------------
def render_realtime(code: str):
    try:
        rt = fetcher.get_realtime_by_code(code)
    except Exception as e:
        st.warning(f"实时行情获取失败：{e}")
        return
    if not rt:
        st.warning("未获取到实时行情")
        return

    price = rt.get("price")
    prev_close = rt.get("prev_close")
    pct = (price / prev_close - 1) * 100 if price and prev_close else 0.0
    up = pct >= 0
    color = "#e74c3c" if up else "#2ecc71"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric(f"{rt.get('name', code)}（{rt.get('code', '')}）",
                  f"{price:.3f}" if price is not None else "—")
    with c2:
        st.markdown(f"### <span style='color:{color}'>{pct:+.2f}%</span>",
                    unsafe_allow_html=True)
        st.caption("涨跌幅")
    with c3:
        st.metric("今开", f"{rt.get('open', 0):.3f}")
    with c4:
        st.metric("最高 / 最低", f"{rt.get('high', 0):.3f} / {rt.get('low', 0):.3f}")
    with c5:
        vol = rt.get("volume", 0) or 0
        amt = rt.get("amount", 0) or 0
        st.metric("成交额", f"{amt / 1e8:.2f}亿")
        st.caption(f"换手 {rt.get('turnover', 0)}%")


# ----------------------------------------------------------------------
# K线图 + 指标副图
# ----------------------------------------------------------------------
def make_candlestick(df: pd.DataFrame, signal_col: str = "signal",
                     show_vol: bool = True, show_macd: bool = True,
                     show_rsi: bool = True, show_kdj: bool = True) -> go.Figure:
    """构建 K线主图 + 成交量 + MACD/RSI/KDJ 副图 + 买卖点"""
    ma_cols = [c for c in df.columns if c.startswith("MA") and c[2:].isdigit()]
    has_macd = {"DIF", "DEA", "MACD"}.issubset(df.columns)
    has_rsi = "RSI" in df.columns
    has_kdj = {"K", "D", "J"}.issubset(df.columns)

    n_rows = 1 + (1 if show_vol else 0) + (1 if show_macd and has_macd else 0) \
             + (1 if show_rsi and has_rsi else 0) + (1 if show_kdj and has_kdj else 0)
    row_heights = [0.5] + [0.15] * (n_rows - 1)

    fig = make_subplots(
        rows=n_rows, cols=1, shared_xaxes=True,
        row_heights=row_heights, vertical_spacing=0.03,
        subplot_titles=(["K线"] + ["成交量"] + (["MACD"] if show_macd and has_macd else [])
                        + (["RSI"] if show_rsi and has_rsi else [])
                        + (["KDJ"] if show_kdj and has_kdj else [])),
    )

    # K线主图
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="K线",
        increasing_line_color="#e74c3c", decreasing_line_color="#2ecc71",
        increasing_fillcolor="#e74c3c", decreasing_fillcolor="#2ecc71",
    ), row=1, col=1)

    # 均线
    colors = ["#f39c12", "#3498db", "#9b59b6", "#e67e22", "#1abc9c"]
    for i, col in enumerate(ma_cols):
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[col], name=col, mode="lines",
            line=dict(width=1.2, color=colors[i % len(colors)]),
        ), row=1, col=1)

    # 布林带（若存在）
    if "BOLL_UP" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["BOLL_UP"], name="BOLL上轨",
            mode="lines", line=dict(width=0.8, color="rgba(127,127,127,0.5)", dash="dot"),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["BOLL_LOW"], name="BOLL下轨",
            mode="lines", line=dict(width=0.8, color="rgba(127,127,127,0.5)", dash="dot"),
            fill="tonexty", fillcolor="rgba(127,127,127,0.08)",
        ), row=1, col=1)

    # 买卖点
    if signal_col in df.columns:
        sig = df[signal_col]
        buy = df[sig > 0]
        sell = df[sig < 0]
        if not buy.empty:
            fig.add_trace(go.Scatter(
                x=buy["date"], y=buy["low"] * 0.99, name="买点",
                mode="markers", marker=dict(symbol="triangle-up", size=12, color="#e74c3c"),
                hovertemplate="买 %{x|%Y-%m-%d}<br>价格 %{y:.2f}<extra></extra>",
            ), row=1, col=1)
        if not sell.empty:
            fig.add_trace(go.Scatter(
                x=sell["date"], y=sell["high"] * 1.01, name="卖点",
                mode="markers", marker=dict(symbol="triangle-down", size=12, color="#2ecc71"),
                hovertemplate="卖 %{x|%Y-%m-%d}<br>价格 %{y:.2f}<extra></extra>",
            ), row=1, col=1)

    row_idx = 2
    # 成交量
    if show_vol:
        colors_vol = ["#e74c3c" if c >= o else "#2ecc71"
                      for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="成交量",
                             marker_color=colors_vol, opacity=0.6), row=row_idx, col=1)
        row_idx += 1

    # MACD
    if show_macd and has_macd:
        fig.add_trace(go.Scatter(x=df["date"], y=df["DIF"], name="DIF",
                                 mode="lines", line=dict(width=1, color="#f39c12")),
                      row=row_idx, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["DEA"], name="DEA",
                                 mode="lines", line=dict(width=1, color="#3498db")),
                      row=row_idx, col=1)
        macd_colors = ["#e74c3c" if v >= 0 else "#2ecc71" for v in df["MACD"]]
        fig.add_trace(go.Bar(x=df["date"], y=df["MACD"], name="MACD柱",
                             marker_color=macd_colors, opacity=0.7), row=row_idx, col=1)
        row_idx += 1

    # RSI
    if show_rsi and has_rsi:
        fig.add_trace(go.Scatter(x=df["date"], y=df["RSI"], name="RSI",
                                 mode="lines", line=dict(width=1.2, color="#9b59b6")),
                      row=row_idx, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(231,76,60,0.4)", row=row_idx, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(46,204,113,0.4)", row=row_idx, col=1)
        fig.update_yaxes(range=[0, 100], row=row_idx, col=1)
        row_idx += 1

    # KDJ
    if show_kdj and has_kdj:
        fig.add_trace(go.Scatter(x=df["date"], y=df["K"], name="K", mode="lines",
                                 line=dict(width=1, color="#f39c12")), row=row_idx, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["D"], name="D", mode="lines",
                                 line=dict(width=1, color="#3498db")), row=row_idx, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["J"], name="J", mode="lines",
                                 line=dict(width=1, color="#9b59b6")), row=row_idx, col=1)
        row_idx += 1

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=780,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        hovermode="x unified",
    )
    return fig


# ----------------------------------------------------------------------
# 回测曲线
# ----------------------------------------------------------------------
def make_equity_chart(equity_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_df["date"], y=equity_df["equity"], name="策略净值",
        mode="lines", line=dict(width=2, color="#3498db"),
    ))
    fig.add_trace(go.Scatter(
        x=equity_df["date"], y=equity_df["benchmark"], name="买入持有",
        mode="lines", line=dict(width=1.5, color="#95a5a6", dash="dot"),
    ))
    fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=40, b=10),
        title="策略净值 vs 基准",
        template="plotly_white", hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------
tab_home, tab_analyze, tab_screener, tab_portfolio, tab_lab, tab_paper = st.tabs([
    "🏠 主页", "📊 行情", "🎯 选股", "💼 组合", "🧪 实验室", "🖥 模拟",
])

# ================= 主页页签 =================
with tab_home:
    st.markdown("### 构建你自己的量化交易平台")
    st.markdown(
        "覆盖 A股 / 港股行情、技术指标、策略回测与参数寻优、模拟交易，"
        "全部数据来自免费公开接口，开箱即用。"
    )

    # 功能卡片
    # 功能卡片
    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown(
            '<div class="qtrader-card">'
            '<div class="card-ico">📊</div>'
            '<div class="card-title">行情分析</div>'
            '<div class="card-desc">A股/港股 K线、实时行情、均线/MACD/RSI/KDJ/BOLL，'
            '单标的策略回测与买卖点标注。</div>'
            '</div>', unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="qtrader-card">'
            '<div class="card-ico">💼</div>'
            '<div class="card-title">组合监控</div>'
            '<div class="card-desc">自选股管理、多标的等权净值与回撤、'
            '多策略实时信号面板。</div>'
            '</div>', unsafe_allow_html=True,
        )
    with colB:
        st.markdown(
            '<div class="qtrader-card">'
            '<div class="card-ico">🎯</div>'
            '<div class="card-title">全市场选股</div>'
            '<div class="card-desc">按均线多头/MACD金叉/RSI超卖/布林突破/放量上涨'
            '多条件扫描，一键生成候选池。</div>'
            '</div>', unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="qtrader-card">'
            '<div class="card-ico">🧪</div>'
            '<div class="card-title">策略实验室</div>'
            '<div class="card-desc">网格参数寻优，找出历史表现最优的策略参数组合，'
            '结果可导出。</div>'
            '</div>', unsafe_allow_html=True,
        )
    with colC:
        st.markdown(
            '<div class="qtrader-card">'
            '<div class="card-ico">🖥</div>'
            '<div class="card-title">模拟交易</div>'
            '<div class="card-desc">虚拟资金纸面交易，记录持仓与盈亏，'
            '练习策略不承担真实风险。</div>'
            '</div>', unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="qtrader-card">'
            '<div class="card-ico">🚀</div>'
            '<div class="card-title">快速开始</div>'
            '<div class="card-desc">在左侧输入代码查询行情；'
            '切到「选股」扫描全市场；「实验室」做参数寻优。</div>'
            '</div>', unsafe_allow_html=True,
        )

    # 数据源说明
    st.divider()
    st.markdown(
        '<div style="display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:0.85rem;">'
        '<span>🔹 数据源：东方财富 + 腾讯（自动切换）</span>'
        '<span>🔹 覆盖：A股 / 港股</span>'
        '<span>🔹 缓存：本地 SQLite</span>'
        '<span>🔹 技术栈：Streamlit + Plotly + pandas</span>'
        '</div>', unsafe_allow_html=True,
    )

# ================= 行情分析页签 =================
with tab_analyze:
    code = st.session_state.get("code") or code

    if code:
        try:
            with st.spinner("正在获取数据..."):
                secid = to_secid(code)
                # 优先读缓存，再拉网络
                df = storage.load_bars(secid, period, fqt)
                if df.empty:
                    df = fetcher.get_kline(secid, period, fqt)
                    if not df.empty:
                        storage.save_bars(secid, period, fqt, df)

            if df.empty:
                st.error(f"未获取到 {code} 的 {period} 数据，请检查代码是否正确")
            else:
                render_realtime(code)
                st.divider()

                # 指标设置
                st.subheader("技术指标")
                ic1, ic2, ic3, ic4 = st.columns(4)
                with ic1:
                    show_vol = st.checkbox("成交量", value=True)
                with ic2:
                    show_macd = st.checkbox("MACD", value=True)
                with ic3:
                    show_rsi = st.checkbox("RSI", value=True)
                with ic4:
                    show_kdj = st.checkbox("KDJ", value=True)

                df_ind = add_indicators(df)

                # 策略回测
                st.divider()
                st.subheader("策略回测")
                with st.expander("回测设置", expanded=True):
                    s1, s2, s3 = st.columns(3)
                    with s1:
                        strat_name = st.selectbox("策略", list(STRATEGY_REGISTRY.keys()))
                    with s2:
                        initial_cash = st.number_input("初始资金", value=100_000.0,
                                                       min_value=1000.0, step=10_000.0)
                    with s3:
                        run_backtest = st.button("▶ 运行回测", type="primary",
                                                 width="stretch")

                if run_backtest:
                    strat_cls = STRATEGY_REGISTRY[strat_name]
                    strat = strat_cls()
                    signal_df = strat.generate_signal(df_ind)
                    engine = BacktestEngine(initial_cash=initial_cash)
                    result = engine.run(signal_df)

                    m1, m2, m3, m4 = st.columns(4)
                    metrics = result["metrics"]
                    fmt = format_metrics(metrics)
                    with m1:
                        st.metric("总收益率", fmt.get("总收益率", "N/A"),
                                  delta=fmt.get("年化收益", ""))
                    with m2:
                        st.metric("最大回撤", fmt.get("最大回撤", "N/A"))
                    with m3:
                        st.metric("夏普比率", fmt.get("夏普比率", "N/A"))
                    with m4:
                        st.metric("交易次数", fmt.get("交易次数", "N/A"))

                    st.plotly_chart(make_equity_chart(result["equity"]),
                                    width="stretch")

                    if not result["trades"].empty:
                        with st.expander("📋 交易明细"):
                            st.dataframe(result["trades"], width="stretch")

                    # 将策略信号画到K线图上
                    df_ind = signal_df

                # K线主图
                st.plotly_chart(
                    make_candlestick(df_ind, "signal", show_vol, show_macd, show_rsi, show_kdj),
                    width="stretch",
                )
        except Exception as e:
            st.error(f"数据获取失败：{e}")
            st.exception(e)

# ================= 选股器页签 =================
with tab_screener:
    st.caption("基于技术指标扫描全市场，一键生成候选池（按成交额取活跃股）")

    sc1, sc2, sc3, sc4 = st.columns([1, 1, 2, 1])
    with sc1:
        scan_market = st.selectbox("市场", ["A股", "港股"], key="scan_market")
    with sc2:
        scan_limit = st.selectbox("扫描数量", [50, 100, 200, 300],
                                  index=1, key="scan_limit",
                                  help="按成交额取前 N 名活跃股扫描")
    with sc3:
        scan_conds = st.multiselect(
            "选股条件（全部命中才入选）",
            list(CONDITIONS.keys()),
            default=["均线多头排列", "放量上涨"],
            key="scan_conds",
        )
    with sc4:
        st.write("")
        st.write("")
        run_scan = st.button("🔍 开始扫描", type="primary", width="stretch",
                             key="run_scan")

    if run_scan:
        if not scan_conds:
            st.warning("请至少选择一个选股条件")
        else:
            screener = Screener()
            progress_bar = st.progress(0, text="扫描中...")

            def _on_progress(done, total):
                progress_bar.progress(done / total,
                                      text=f"扫描中 {done}/{total} ...")

            with st.spinner("正在扫描全市场，请稍候..."):
                result = screener.scan(
                    market=scan_market,
                    limit=scan_limit,
                    conditions=scan_conds,
                    progress=_on_progress,
                )

            if result.empty:
                st.info("本轮未发现符合全部条件的股票，可放宽条件或扩大扫描范围")
            else:
                st.success(f"🎉 找到 {len(result)} 只符合条件的股票")
                st.dataframe(
                    result.rename(columns={
                        "code": "代码", "name": "名称", "price": "现价",
                        "pct_chg": "涨跌幅%", "volume_ratio": "量比",
                        "RSI": "RSI", "matched": "命中条件数",
                        "details": "命中条件",
                    }),
                    width="stretch", height=420,
                )
                csv = result.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ 下载候选池 CSV", csv,
                    file_name=f"qtrader_screener_{scan_market}.csv",
                    mime="text/csv",
                )

# ================= 组合监控页签 =================
with tab_portfolio:
    st.caption("管理自选股，查看各标的策略信号与组合净值曲线")

    # ---- 添加自选 ----
    wc1, wc2, wc3 = st.columns([2, 2, 1])
    with wc1:
        wl_code = st.text_input("添加自选代码（A股6位 / 港股5位）", "",
                                key="wl_code")
    with wc2:
        wl_market = st.selectbox("市场", ["A股", "港股"], key="wl_market")
    with wc3:
        st.write("")
        st.write("")
        wl_add = st.button("➕ 添加", width="stretch", key="wl_add")

    if wl_add and wl_code.strip():
        code_in = wl_code.strip().upper().replace(".", "")
        try:
            rt = fetcher.get_realtime_by_code(code_in)
            name = rt.get("name", "") if rt else ""
            ok = watchlist.add(code_in, name, wl_market)
            st.success(f"已{'新增' if ok else '已在'}自选：{code_in} {name}")
        except Exception as e:
            st.error(f"添加失败（代码可能无效）：{e}")

    st.divider()

    # ---- 自选列表 ----
    items = watchlist.get_all()
    if not items:
        st.info("自选股为空。先在左侧输入代码添加，或从选股器结果中挑选。")
    else:
        display_rows = []
        for it in items:
            try:
                rt = fetcher.get_realtime_by_code(it["code"])
                price = rt.get("price")
                prev = rt.get("prev_close")
                pct = (price / prev - 1) * 100 if price and prev else 0.0
                display_rows.append({
                    "代码": it["code"],
                    "名称": rt.get("name") or it.get("name") or "",
                    "现价": price,
                    "涨跌幅%": round(float(pct), 2),
                })
            except Exception:
                display_rows.append({"代码": it["code"],
                                     "名称": it.get("name") or "",
                                     "现价": None, "涨跌幅%": None})

        st.dataframe(pd.DataFrame(display_rows), width="stretch", height=240)

        # ---- 删除自选 ----
        rm_col1, rm_col2 = st.columns([2, 1])
        with rm_col1:
            rm_code = st.selectbox("从自选中移除", [it["code"] for it in items],
                                   key="rm_code")
        with rm_col2:
            st.write("")
            st.write("")
            if st.button("🗑 移除", width="stretch", key="rm_btn"):
                watchlist.remove(rm_code)
                st.rerun()

    st.divider()

    # ---- 策略信号面板 ----
    if items:
        st.subheader("📶 策略信号面板")
        signal_rows = []
        for it in items:
            code_i = it["code"]
            try:
                df_i = load_bars_cached(code_i, beg="0")
                if df_i.empty or len(df_i) < 70:
                    continue
                dfi = add_indicators(df_i)
                sig_cells = []
                for sname, scls in STRATEGY_REGISTRY.items():
                    s = scls()
                    sdf = s.generate_signal(dfi)
                    last_sig = sdf["signal"].iloc[-1]
                    label = "🔴买" if last_sig > 0 else ("🟢卖" if last_sig < 0 else "—")
                    sig_cells.append(label)
                last = dfi.iloc[-1]
                signal_rows.append({
                    "代码": code_i,
                    "名称": it.get("name") or "",
                    "收盘": round(float(last["close"]), 3),
                    "RSI": round(float(last["RSI"]), 1),
                    **{f"{n}": sig_cells[i] for i, n in enumerate(STRATEGY_REGISTRY.keys())},
                })
            except Exception:
                continue
        if signal_rows:
            st.dataframe(pd.DataFrame(signal_rows), width="stretch", height=260)
        else:
            st.info("暂无信号数据")

        # ---- 组合净值 ----
        st.divider()
        st.subheader("📈 组合净值（等权）")
        p1, p2 = st.columns(2)
        with p1:
            combo_cash = st.number_input("组合初始资金", value=1_000_000.0,
                                         min_value=1000.0, step=100_000.0,
                                         key="combo_cash")
        with p2:
            combo_days = st.selectbox("回看区间", ["近1年", "近2年", "全部"],
                                      index=0, key="combo_days")

        beg_map = {"近1年": "20250101", "近2年": "20240101", "全部": "0"}
        beg_s = beg_map.get(combo_days, "0")

        if st.button("📊 计算组合净值", key="combo_calc", type="primary"):
            codes_list = [it["code"] for it in items]
            eq = portfolio_equity(codes_list, initial_cash=combo_cash, beg=beg_s)
            if eq.empty:
                st.warning("组合计算失败：请检查自选股代码是否有效")
            else:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=eq["date"], y=eq["equity"], name="组合净值",
                    mode="lines", line=dict(width=2, color="#3498db"),
                ))
                # 组合最大回撤
                cum_max = eq["equity"].cummax()
                dd = (eq["equity"] / cum_max - 1)
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=eq["date"], y=dd * 100, name="回撤%",
                    mode="lines", fill="tozeroy",
                    line=dict(width=1, color="#e74c3c"),
                ))
                fig.update_layout(
                    height=320, margin=dict(l=10, r=10, t=40, b=10),
                    title="组合净值曲线", template="plotly_white",
                    hovermode="x unified",
                )
                fig2.update_layout(
                    height=200, margin=dict(l=10, r=10, t=40, b=10),
                    title="组合回撤（%）", template="plotly_white",
                    hovermode="x unified",
                )
                st.plotly_chart(fig, width="stretch")
                st.plotly_chart(fig2, width="stretch")

                total_ret = (eq["equity"].iloc[-1] / combo_cash - 1) * 100
                max_dd = dd.min() * 100
                m1, m2, m3 = st.columns(3)
                m1.metric("组合总收益", f"{total_ret:.2f}%")
                m2.metric("最大回撤", f"{max_dd:.2f}%")
                m3.metric("期末净值", f"{eq['equity'].iloc[-1]:,.0f}")

# ================= 策略实验室页签 =================
with tab_lab:
    st.caption("对内置策略做参数网格搜索，找出历史表现最优的参数组合")

    l1, l2, l3, l4 = st.columns([1, 1, 1, 1])
    with l1:
        lab_code = st.text_input("股票代码", "600519", key="lab_code")
    with l2:
        lab_strat = st.selectbox("策略", list(PARAM_GRIDS.keys()), key="lab_strat")
    with l3:
        lab_metric = st.selectbox(
            "寻优指标",
            ["年化收益", "总收益率", "夏普比率", "最大回撤"],
            key="lab_metric",
        )
    with l4:
        lab_topn = st.selectbox("Top N", [5, 10, 20], index=1, key="lab_topn")

    lab_note = " / ".join(
        f"{k}={v}" for k, v in PARAM_GRIDS.get(lab_strat, {}).items()
    )
    st.caption(f"参数网格：{lab_note}")

    if st.button("🚀 开始寻优", type="primary", key="lab_run"):
        try:
            progress_bar = st.progress(0, text="寻优中...")

            def _on_progress(done, total):
                progress_bar.progress(done / total,
                                      text=f"寻优中 {done}/{total} ...")

            with st.spinner("正在遍历参数组合..."):
                best = optimize(
                    code=lab_code.strip(),
                    strategy_name=lab_strat,
                    metric=lab_metric,
                    top_n=lab_topn,
                    progress=_on_progress,
                )

            if best.empty:
                st.warning("寻优无结果，请检查代码或参数范围")
            else:
                st.success("寻优完成")
                show = best.copy()
                show["总收益率%"] = (show["总收益率"] * 100).round(2)
                show["年化收益%"] = (show["年化收益"] * 100).round(2)
                show["最大回撤%"] = (show["最大回撤"] * 100).round(2)
                show["夏普"] = show["夏普比率"].round(2)
                show["胜率%"] = (show["胜率"] * 100).round(1)
                drop_cols = ["总收益率", "年化收益", "最大回撤",
                             "夏普比率", "胜率", "期末资产"]
                show = show.drop(columns=drop_cols, errors="ignore")
                st.dataframe(show, width="stretch", height=360)

                csv = best.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ 下载寻优结果 CSV", csv,
                    file_name=f"qtrader_opt_{lab_strat}_{lab_code}.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.error(f"寻优失败：{e}")

# ================= 模拟交易页签 =================
with tab_paper:
    st.caption("纸面交易：用虚拟资金练习策略，不涉及真实资金")

    cash = paper_account.get_cash()
    positions = paper_account.get_positions()

    # 账户总览
    c1, c2, c3 = st.columns(3)
    c1.metric("可用资金", f"{cash:,.0f}")
    c2.metric("持仓数", f"{len(positions)}")

    # 持仓市值
    market_val = 0.0
    for pos in positions:
        try:
            rt = fetcher.get_realtime_by_code(pos["code"])
            price = rt.get("price")
            if price:
                market_val += price * pos["qty"]
        except Exception:
            pass
    c3.metric("持仓市值", f"{market_val:,.0f}")
    st.caption(f"总资产 ≈ {cash + market_val:,.0f}（现金 + 持仓市值）")

    st.divider()

    # 下单面板
    st.subheader("下单")
    o1, o2, o3, o4, o5 = st.columns([1, 1, 1, 1, 1])
    with o1:
        trade_code = st.text_input("代码", "600519", key="trade_code")
    with o2:
        trade_side = st.selectbox("方向", ["买入", "卖出"], key="trade_side")
    with o3:
        trade_qty = st.number_input("数量", value=100.0, min_value=100.0,
                                    step=100.0, key="trade_qty")
    with o4:
        trade_price = st.number_input("价格", value=0.0, min_value=0.0,
                                      step=0.01, key="trade_price",
                                      help="留 0 则用实时价")
    with o5:
        st.write("")
        st.write("")
        trade_go = st.button("⚡ 下单", type="primary", width="stretch",
                             key="trade_go")

    if trade_go and trade_code.strip():
        code_t = trade_code.strip().upper().replace(".", "")
        price_t = trade_price if trade_price > 0 else None
        try:
            rt = fetcher.get_realtime_by_code(code_t)
            name_t = rt.get("name", "") if rt else ""
            if price_t is None:
                price_t = rt.get("price") if rt else None
            if not price_t:
                st.error("无法获取价格，请手动输入")
            else:
                if trade_side == "买入":
                    msg = paper_account.buy(code_t, name_t, trade_qty, float(price_t))
                else:
                    msg = paper_account.sell(code_t, float(price_t), trade_qty)
                st.success(msg)
                st.rerun()
        except Exception as e:
            st.error(f"下单失败：{e}")

    st.divider()

    # 持仓明细
    st.subheader("持仓明细")
    if not positions:
        st.info("暂无持仓")
    else:
        pos_rows = []
        for pos in positions:
            try:
                rt = fetcher.get_realtime_by_code(pos["code"])
                price = rt.get("price") or pos["avg_cost"]
                value = price * pos["qty"]
                pnl = (price - pos["avg_cost"]) * pos["qty"]
                pnl_pct = (price / pos["avg_cost"] - 1) * 100 if pos["avg_cost"] else 0
                pos_rows.append({
                    "代码": pos["code"], "名称": pos.get("name") or "",
                    "数量": pos["qty"], "成本": round(pos["avg_cost"], 3),
                    "现价": round(float(price), 3),
                    "市值": round(value, 0),
                    "浮动盈亏": round(pnl, 0),
                    "盈亏%": round(float(pnl_pct), 2),
                })
            except Exception:
                pos_rows.append({
                    "代码": pos["code"], "名称": pos.get("name") or "",
                    "数量": pos["qty"], "成本": round(pos["avg_cost"], 3),
                    "现价": None, "市值": None, "浮动盈亏": None, "盈亏%": None,
                })
        st.dataframe(pd.DataFrame(pos_rows), width="stretch", height=240)

    st.divider()

    # 成交记录
    trades = paper_account.get_trades(limit=50)
    if trades:
        st.subheader("最近成交")
        st.dataframe(pd.DataFrame(trades), width="stretch", height=260)

    # 重置
    if st.button("🔄 重置账户", key="paper_reset"):
        paper_account.reset()
        st.success("账户已重置")
        st.rerun()

# 底部：市场热榜
# ----------------------------------------------------------------------
st.divider()
st.subheader(f"🔥 {market} 热榜")
with st.spinner("加载榜单..."):
    try:
        rank_df = fetcher.get_stock_list(market, limit=rank_n, sort_field=rank_field)
        if not rank_df.empty:
            st.dataframe(
                rank_df.rename(columns={
                    "code": "代码", "name": "名称", "price": "现价",
                    "pct_chg": "涨跌幅%", "chg": "涨跌额",
                    "volume": "成交量(手)", "amount": "成交额",
                    "turnover": "换手%", "pe": "市盈率",
                    "volume_ratio": "量比", "high": "最高", "low": "最低",
                    "open": "开盘", "prev_close": "昨收",
                    "total_mv": "总市值", "float_mv": "流通市值",
                }),
                width="stretch", height=380,
            )
    except Exception as e:
        st.warning(f"榜单加载失败：{e}")

st.caption("⚠️ 数据来自东方财富免费接口，仅供学习研究，不构成投资建议。")
