"""Streamlit 주식 데이터 분석기."""

from datetime import date, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

PERIOD_OPTIONS = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
}

# 이동평균 계산을 위해 표시 기간보다 넉넉히 조회
FETCH_PERIOD_FOR_MA = {
    "1mo": "6mo",
    "3mo": "1y",
    "6mo": "2y",
    "1y": "2y",
}

MA20_COLOR = "orange"
MA60_COLOR = "green"

COMPARE_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(symbol: str, period: str) -> tuple[dict, object]:
    """yfinance로 종목 정보와 역사적 시세(이동평균 포함)를 가져온다."""
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    hist_display = ticker.history(period=period)
    hist_full = ticker.history(period=FETCH_PERIOD_FOR_MA.get(period, period))

    if not hist_full.empty:
        hist_full = hist_full.copy()
        hist_full["MA20"] = hist_full["Close"].rolling(window=20, min_periods=20).mean()
        hist_full["MA60"] = hist_full["Close"].rolling(window=60, min_periods=60).mean()

    if hist_display.empty:
        return info, hist_display

    hist = hist_display.copy()
    if not hist_full.empty:
        hist["MA20"] = hist_full["MA20"].reindex(hist.index)
        hist["MA60"] = hist_full["MA60"].reindex(hist.index)
    else:
        hist["MA20"] = hist["Close"].rolling(window=20, min_periods=20).mean()
        hist["MA60"] = hist["Close"].rolling(window=60, min_periods=60).mean()

    return info, hist


@st.cache_data(ttl=300, show_spinner=False)
def fetch_comparison_data(
    symbols: tuple[str, ...], period: str
) -> tuple[dict[str, object], dict[str, str], list[str]]:
    """여러 종목의 종가와 회사명을 가져온다. 실패한 종목은 errors에 담는다."""
    closes: dict[str, object] = {}
    names: dict[str, str] = {}
    errors: list[str] = []

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            hist = ticker.history(period=period)
            if hist.empty or "Close" not in hist.columns:
                errors.append(symbol)
                continue
            name = info.get("longName") or info.get("shortName") or symbol
            names[symbol] = name
            closes[symbol] = hist["Close"]
        except Exception:  # noqa: BLE001 - 개별 종목 실패는 목록으로 안내
            errors.append(symbol)

    return closes, names, errors


def parse_symbols(raw: str) -> list[str]:
    """쉼표로 구분된 종목 코드를 파싱한다."""
    parts = [part.strip().upper() for part in raw.replace("，", ",").split(",")]
    seen: set[str] = set()
    symbols: list[str] = []
    for part in parts:
        if part and part not in seen:
            seen.add(part)
            symbols.append(part)
    return symbols


def format_price(symbol: str, price: float | None) -> str:
    if price is None:
        return "N/A"
    if symbol.upper().endswith((".KS", ".KQ")):
        return f"{price:,.0f}원"
    return f"${price:,.2f}"


def format_money(symbol: str, amount: float) -> str:
    if symbol.upper().endswith((".KS", ".KQ")):
        return f"{amount:,.0f}원"
    return f"${amount:,.2f}"


@st.cache_data(ttl=300, show_spinner=False)
def calculate_return(
    symbol: str, buy_date: date, buy_amount: float
) -> dict | None:
    """매수일 종가 기준 현재 가치와 수익률을 계산한다."""
    if buy_amount <= 0:
        return None

    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    company_name = info.get("longName") or info.get("shortName") or symbol

    # 매수일 당일이 휴장이면 이후 첫 거래일 종가를 사용
    end_date = date.today() + timedelta(days=1)
    hist = ticker.history(start=buy_date, end=end_date)
    if hist.empty or "Close" not in hist.columns:
        return None

    buy_price = float(hist["Close"].iloc[0])
    current_price = float(hist["Close"].iloc[-1])
    if buy_price <= 0:
        return None

    shares = buy_amount / buy_price
    current_value = shares * current_price
    profit = current_value - buy_amount
    return_pct = (current_value / buy_amount - 1.0) * 100.0
    actual_buy_date = hist.index[0].date()

    return {
        "company_name": company_name,
        "buy_price": buy_price,
        "actual_buy_date": actual_buy_date,
        "current_price": current_price,
        "shares": shares,
        "current_value": current_value,
        "profit": profit,
        "return_pct": return_pct,
    }


def _chart_frame(hist):
    chart_df = hist.reset_index()
    date_col = "Date" if "Date" in chart_df.columns else chart_df.columns[0]
    return chart_df, date_col


def _price_axis_label(symbol: str) -> str:
    return "가격 (원)" if symbol.upper().endswith((".KS", ".KQ")) else "가격 (USD)"


def _add_moving_averages(fig, chart_df, date_col, show_ma20: bool, show_ma60: bool, row=None):
    """체크된 이동평균선을 figure에 추가한다."""
    kwargs = {"row": row, "col": 1} if row is not None else {}

    if show_ma20 and "MA20" in chart_df.columns:
        fig.add_trace(
            go.Scatter(
                x=chart_df[date_col],
                y=chart_df["MA20"],
                mode="lines",
                name="MA20",
                line=dict(color=MA20_COLOR, width=2),
                hovertemplate="날짜=%{x|%Y-%m-%d}<br>MA20=%{y:,.2f}<extra></extra>",
            ),
            **kwargs,
        )

    if show_ma60 and "MA60" in chart_df.columns:
        fig.add_trace(
            go.Scatter(
                x=chart_df[date_col],
                y=chart_df["MA60"],
                mode="lines",
                name="MA60",
                line=dict(color=MA60_COLOR, width=2),
                hovertemplate="날짜=%{x|%Y-%m-%d}<br>MA60=%{y:,.2f}<extra></extra>",
            ),
            **kwargs,
        )


def build_price_chart(hist, company_name: str, symbol: str, show_ma20: bool, show_ma60: bool):
    """종가 기준 주가 추이 선 차트를 만든다."""
    chart_df, date_col = _chart_frame(hist)
    price_label = _price_axis_label(symbol)
    is_kr = symbol.upper().endswith((".KS", ".KQ"))
    hover_price = "%{y:,.0f}원" if is_kr else "$%{y:,.2f}"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df[date_col],
            y=chart_df["Close"],
            mode="lines",
            name="종가",
            line=dict(width=2),
            hovertemplate=f"날짜=%{{x|%Y-%m-%d}}<br>가격={hover_price}<extra></extra>",
        )
    )
    _add_moving_averages(fig, chart_df, date_col, show_ma20, show_ma60)

    fig.update_layout(
        title=f"{company_name} 주가 추이",
        xaxis_title="날짜",
        yaxis_title=price_label,
        height=500,
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_candlestick_chart(
    hist, company_name: str, symbol: str, show_ma20: bool, show_ma60: bool
):
    """캔들스틱 + 거래량 차트를 만든다. 상승=파랑, 하락=빨강, x축 연동."""
    chart_df, date_col = _chart_frame(hist)
    price_label = _price_axis_label(symbol)

    volume_avg = chart_df["Volume"].mean()
    is_up = chart_df["Close"] >= chart_df["Open"]
    is_high_volume = chart_df["Volume"] >= volume_avg

    volume_colors = []
    for up, high_vol in zip(is_up, is_high_volume, strict=True):
        if high_vol:
            volume_colors.append("#1E88E5" if up else "#E53935")
        else:
            volume_colors.append("#90CAF9" if up else "#EF9A9A")

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{company_name} 주가 추이", "거래량"),
    )

    fig.add_trace(
        go.Candlestick(
            x=chart_df[date_col],
            open=chart_df["Open"],
            high=chart_df["High"],
            low=chart_df["Low"],
            close=chart_df["Close"],
            increasing_line_color="blue",
            increasing_fillcolor="blue",
            decreasing_line_color="red",
            decreasing_fillcolor="red",
            name="OHLC",
        ),
        row=1,
        col=1,
    )
    _add_moving_averages(fig, chart_df, date_col, show_ma20, show_ma60, row=1)

    fig.add_trace(
        go.Bar(
            x=chart_df[date_col],
            y=chart_df["Volume"],
            marker_color=volume_colors,
            name="거래량",
            hovertemplate="날짜=%{x|%Y-%m-%d}<br>거래량=%{y:,.0f}<extra></extra>",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig.add_hline(
        y=volume_avg,
        line_dash="dot",
        line_color="gray",
        annotation_text="평균 거래량",
        annotation_position="top left",
        row=2,
        col=1,
    )

    fig.update_layout(
        height=700,
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text=price_label, row=1, col=1)
    fig.update_yaxes(title_text="거래량", row=2, col=1)
    fig.update_xaxes(title_text="날짜", row=2, col=1)
    return fig


def build_comparison_chart(
    closes: dict[str, object], names: dict[str, str]
) -> go.Figure:
    """시작일 기준 수익률(%)로 정규화한 비교 선 차트를 만든다."""
    fig = go.Figure()

    for idx, (symbol, close) in enumerate(closes.items()):
        series = close.dropna()
        if series.empty:
            continue
        base = series.iloc[0]
        if base == 0:
            continue
        normalized = (series / base - 1.0) * 100.0
        company_name = names.get(symbol, symbol)
        color = COMPARE_COLORS[idx % len(COMPARE_COLORS)]

        fig.add_trace(
            go.Scatter(
                x=normalized.index,
                y=normalized.values,
                mode="lines",
                name=company_name,
                line=dict(color=color, width=2),
                hovertemplate=(
                    f"{company_name}<br>"
                    "날짜=%{x|%Y-%m-%d}<br>"
                    "수익률=%{y:.2f}%<extra></extra>"
                ),
            )
        )

    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="종목 비교 (시작일 기준 수익률)",
        xaxis_title="날짜",
        yaxis_title="수익률 (%)",
        height=550,
        margin=dict(l=40, r=20, t=60, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def render_single_stock_tab() -> None:
    with st.form("stock_query_form"):
        symbol_input = st.text_input("종목 코드", value="005930.KS")
        period_label = st.selectbox("기간 선택", list(PERIOD_OPTIONS.keys()), key="single_period")
        submitted = st.form_submit_button("데이터 조회", type="primary")

    if submitted:
        symbol = symbol_input.strip()
        if not symbol:
            st.error("종목 코드를 입력해 주세요.")
            st.session_state.pop("stock_result", None)
        else:
            period = PERIOD_OPTIONS[period_label]
            with st.spinner("데이터를 조회하는 중..."):
                try:
                    info, hist = fetch_stock_data(symbol, period)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"데이터 조회에 실패했습니다: {exc}")
                    st.session_state.pop("stock_result", None)
                else:
                    company_name = info.get("longName") or info.get("shortName")
                    if not company_name and (hist is None or hist.empty):
                        st.error(
                            "유효한 종목 데이터를 찾지 못했습니다. 종목 코드를 확인해 주세요."
                        )
                        st.session_state.pop("stock_result", None)
                    else:
                        st.session_state["stock_result"] = {
                            "symbol": symbol,
                            "info": info,
                            "hist": hist,
                            "company_name": company_name,
                        }

    if "stock_result" not in st.session_state:
        return

    result = st.session_state["stock_result"]
    symbol = result["symbol"]
    info = result["info"]
    hist = result["hist"]
    company_name = result["company_name"]
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    change_pct = info.get("regularMarketChangePercent")
    display_name = company_name or symbol

    st.success("데이터 조회가 완료되었습니다.")
    st.write(f"**회사명:** {company_name or 'N/A'}")
    st.write(f"**현재가:** {format_price(symbol, current_price)}")
    if change_pct is not None:
        st.write(f"**전일 대비 등락률:** {change_pct:+.2f}%")
    else:
        st.write("**전일 대비 등락률:** N/A")

    if hist is None or hist.empty:
        st.warning("선택한 기간의 역사적 데이터가 없습니다.")
        return

    with st.container(horizontal=True, gap="medium"):
        show_ma20 = st.checkbox("20일 이동평균 (주황)", value=True)
        show_ma60 = st.checkbox("60일 이동평균 (초록)", value=True)

    line_tab, candle_tab = st.tabs(["선 차트", "캔들스틱 챠트"])

    with line_tab:
        st.plotly_chart(
            build_price_chart(hist, display_name, symbol, show_ma20, show_ma60),
            width="stretch",
        )

    with candle_tab:
        st.plotly_chart(
            build_candlestick_chart(hist, display_name, symbol, show_ma20, show_ma60),
            width="stretch",
        )

    st.subheader("역사적 데이터")
    st.dataframe(hist, width="stretch")


def render_compare_tab() -> None:
    with st.form("compare_query_form"):
        symbols_input = st.text_input(
            "종목 코드 (쉼표로 구분)",
            value="005930.KS, 000660.KS",
            help="예: 005930.KS, 000660.KS, AAPL",
        )
        period_label = st.selectbox(
            "기간 선택", list(PERIOD_OPTIONS.keys()), key="compare_period"
        )
        submitted = st.form_submit_button("비교 조회", type="primary")

    if submitted:
        symbols = parse_symbols(symbols_input)
        if len(symbols) < 2:
            st.error("비교하려면 종목 코드를 2개 이상 입력해 주세요.")
            st.session_state.pop("compare_result", None)
        else:
            period = PERIOD_OPTIONS[period_label]
            with st.spinner("비교 데이터를 조회하는 중..."):
                closes, names, errors = fetch_comparison_data(tuple(symbols), period)
                if len(closes) < 2:
                    st.error("비교 가능한 종목이 2개 미만입니다. 종목 코드를 확인해 주세요.")
                    if errors:
                        st.warning("조회 실패: " + ", ".join(errors))
                    st.session_state.pop("compare_result", None)
                else:
                    st.session_state["compare_result"] = {
                        "closes": closes,
                        "names": names,
                        "errors": errors,
                        "symbols": list(closes.keys()),
                    }

    if "compare_result" not in st.session_state:
        return

    result = st.session_state["compare_result"]
    closes = result["closes"]
    names = result["names"]
    errors = result["errors"]

    st.success("종목 비교 조회가 완료되었습니다.")
    if errors:
        st.warning("일부 종목 조회 실패: " + ", ".join(errors))

    st.caption("각 종목의 시작일 종가를 0%로 두고 이후 수익률을 비교합니다.")
    st.plotly_chart(build_comparison_chart(closes, names), width="stretch")

    latest_rows = []
    for symbol, close in closes.items():
        series = close.dropna()
        if series.empty:
            continue
        ret = (series.iloc[-1] / series.iloc[0] - 1.0) * 100.0
        latest_rows.append(
            {
                "종목 코드": symbol,
                "종목명": names.get(symbol, symbol),
                "기간 수익률 (%)": round(float(ret), 2),
            }
        )
    if latest_rows:
        st.subheader("기간 수익률 요약")
        st.dataframe(latest_rows, width="stretch", hide_index=True)


def render_return_calculator() -> None:
    """메인 탭용 수익률 계산기 (모바일 반응형)."""
    default_symbol = "005930.KS"
    if "stock_result" in st.session_state:
        default_symbol = st.session_state["stock_result"].get("symbol", default_symbol)

    st.caption("매수일과 금액을 입력하면 현재 가치와 수익률을 계산합니다.")

    with st.form("return_calculator_form", clear_on_submit=False):
        symbol = st.text_input(
            "종목 코드",
            value=default_symbol,
            key="calc_symbol",
        ).strip()

        # 좁은 화면에서는 세로로, 넓은 화면에서는 가로로 배치
        date_col, amount_col = st.columns(2)
        with date_col:
            buy_date = st.date_input(
                "매수 날짜",
                value=date.today() - timedelta(days=90),
                max_value=date.today(),
                key="calc_buy_date",
            )
        with amount_col:
            is_kr = symbol.upper().endswith((".KS", ".KQ"))
            default_amount = 1_000_000.0 if is_kr else 1000.0
            buy_amount = st.number_input(
                "매수 금액",
                min_value=0.0,
                value=default_amount,
                step=10000.0 if is_kr else 100.0,
                key="calc_buy_amount",
            )

        submitted = st.form_submit_button("수익률 계산", type="primary", width="stretch")

    if submitted:
        st.session_state["calc_auto_result"] = True
        st.session_state["calc_last_symbol"] = symbol
        st.session_state["calc_last_buy_date"] = buy_date
        st.session_state["calc_last_buy_amount"] = float(buy_amount)

    if not st.session_state.get("calc_auto_result"):
        return

    symbol = st.session_state.get("calc_last_symbol", symbol)
    buy_date = st.session_state.get("calc_last_buy_date", buy_date)
    buy_amount = st.session_state.get("calc_last_buy_amount", float(buy_amount))

    if not symbol:
        st.error("종목 코드를 입력해 주세요.")
        return
    if buy_amount <= 0:
        st.error("매수 금액은 0보다 커야 합니다.")
        return

    with st.spinner("계산 중..."):
        try:
            result = calculate_return(symbol, buy_date, float(buy_amount))
        except Exception as exc:  # noqa: BLE001
            st.error(f"계산 실패: {exc}")
            return

    if result is None:
        st.error("해당 기간의 시세를 찾지 못했습니다.")
        return

    is_profit = result["return_pct"] >= 0
    color = "blue" if is_profit else "red"

    st.success(f"{result['company_name']} ({symbol})")
    if result["actual_buy_date"] != buy_date:
        st.caption(f"실제 적용 매수일: {result['actual_buy_date']} (휴장일 보정)")

    price_col, value_col = st.columns(2)
    with price_col:
        st.metric("매수가", format_price(symbol, result["buy_price"]))
        st.metric("현재가", format_price(symbol, result["current_price"]))
    with value_col:
        st.metric("현재 가치", format_money(symbol, result["current_value"]))
        st.metric("수익/손실", format_money(symbol, result["profit"]))

    st.markdown(
        f":{color}[**수익률: {result['return_pct']:+.2f}%**]"
    )


def apply_theme_preference(mode: str) -> None:
    """낮/밤/시스템 테마를 적용한다."""
    # 시스템 테마 판별용 쿠키 갱신 (다음 요청부터 사용)
    st.html(
        """
        <script>
        (function () {
          try {
            const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.cookie = 'hs_prefers_color=' + (dark ? 'dark' : 'light')
              + '; path=/; max-age=31536000; SameSite=Lax';
          } catch (e) {}
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )

    if mode == "light":
        st._config.set_option("theme.base", "light")
        return
    if mode == "dark":
        st._config.set_option("theme.base", "dark")
        return

    # system: OS 선호 쿠키 → 없으면 현재 테마 타입 사용
    preferred = ""
    try:
        preferred = (st.context.cookies or {}).get("hs_prefers_color", "")
    except Exception:  # noqa: BLE001
        preferred = ""
    if preferred not in ("light", "dark"):
        try:
            preferred = st.context.theme.type
        except Exception:  # noqa: BLE001
            preferred = "light"
    if preferred not in ("light", "dark"):
        preferred = "light"
    st._config.set_option("theme.base", preferred)


def render_theme_toggle() -> None:
    """화면 상단 오른쪽: 클릭 시 낮 → 밤 → 시스템 순환 토글."""
    theme_cycle = ("light", "dark", "system")
    theme_meta = {
        "light": (":material/light_mode:", "낮", "현재: 낮 (라이트) — 클릭하면 밤으로"),
        "dark": (":material/dark_mode:", "밤", "현재: 밤 (다크) — 클릭하면 시스템으로"),
        "system": (
            ":material/brightness_auto:",
            "시스템",
            "현재: 시스템 — 클릭하면 낮으로",
        ),
    }

    if "ui_theme" not in st.session_state:
        st.session_state["ui_theme"] = "system"

    current = st.session_state["ui_theme"]
    if current not in theme_meta:
        current = "system"
        st.session_state["ui_theme"] = current

    apply_theme_preference(current)

    icon, label, help_text = theme_meta[current]
    with st.container(
        horizontal=True,
        gap="small",
        wrap=False,
        horizontal_alignment="right",
        key="theme_toggle_bar",
    ):
        if st.button(
            label,
            key="theme_cycle_toggle",
            icon=icon,
            help=help_text,
            type="secondary",
            width="content",
        ):
            idx = theme_cycle.index(current)
            next_mode = theme_cycle[(idx + 1) % len(theme_cycle)]
            st.session_state["ui_theme"] = next_mode
            apply_theme_preference(next_mode)
            st.rerun()


st.set_page_config(
    page_title="주식 데이터 분석기",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": None,
    },
)
# 상단 Share/메뉴 숨김 + 모바일 레이아웃
st.html((Path(__file__).parent / ".streamlit" / "hide_chrome.css"))

render_theme_toggle()

st.title("주식 데이터 분석기")

if "main_tab" not in st.session_state:
    st.session_state["main_tab"] = "단일 종목"

# 왼쪽: 단일 종목·종목 비교 / 오른쪽 끝: 수익률 계산기
with st.container(horizontal=True, gap="small", wrap=False, key="main_nav_row"):
    for label in ("단일 종목", "종목 비교"):
        is_active = st.session_state["main_tab"] == label
        if st.button(
            label,
            key=f"nav_{label}",
            type="primary" if is_active else "secondary",
            width="content",
        ):
            st.session_state["main_tab"] = label
            st.rerun()

    st.html('<div class="main-nav-spacer" aria-hidden="true"></div>')

    calc_label = "수익률 계산기"
    calc_active = st.session_state["main_tab"] == calc_label
    if st.button(
        calc_label,
        key="nav_calc",
        type="primary" if calc_active else "secondary",
        width="content",
    ):
        st.session_state["main_tab"] = calc_label
        st.rerun()

active = st.session_state["main_tab"]
if active == "단일 종목":
    render_single_stock_tab()
elif active == "종목 비교":
    render_compare_tab()
else:
    render_return_calculator()
