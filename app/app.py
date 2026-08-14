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
from screener.screener import CONDITIONS, Screener
from strategies.base import STRATEGY_REGISTRY


# ----------------------------------------------------------------------
# 页面基础
# ----------------------------------------------------------------------
st.set_page_config(page_title="QTrader 量化平台", layout="wide",
                   page_icon="📈")
st.title("📈 QTrader 个人量化交易平台")
st.caption("数据源：东方财富（免费） | 支持 A股 / 港股 | 本地 SQLite 缓存")


# ----------------------------------------------------------------------
# 侧边栏：行情设置
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("行情设置")
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
tab_analyze, tab_screener = st.tabs(["📊 行情分析", "🎯 选股器"])

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
    st.subheader("🎯 全市场选股器")
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
