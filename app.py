"""
IDX Stock Screener & Technical Signal Dashboard
------------------------------------------------
Aplikasi web (Streamlit) untuk membantu keputusan jual/beli saham IDX
berdasarkan analisis teknikal otomatis dari data yfinance.

PENTING: Ini adalah alat bantu analisis teknikal, BUKAN nasihat keuangan.
Semua sinyal dihasilkan dari aturan matematis (indikator teknikal) dan
bisa salah. Selalu lakukan riset tambahan (fundamental, berita, dsb)
dan gunakan manajemen risiko (stop loss, position sizing) sendiri.

Cara jalankan:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ----------------------------------------------------------------------------
# KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="IDX Stock Screener",
    page_icon="📈",
    layout="wide",
)

DEFAULT_TICKERS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK",
    "UNVR.JK", "ICBP.JK", "ADRO.JK", "ANTM.JK", "PGAS.JK", "PTBA.JK",
    "INDF.JK", "KLBF.JK", "SMGR.JK", "GGRM.JK", "HMSP.JK", "UNTR.JK",
    "CPIN.JK", "JSMR.JK", "EXCL.JK", "TOWR.JK", "MDKA.JK", "BRPT.JK",
    "TPIA.JK", "ITMG.JK", "INCO.JK", "AKRA.JK", "MEDC.JK", "BUKA.JK",
]

# ----------------------------------------------------------------------------
# INDIKATOR TEKNIKAL (dihitung manual pakai pandas/numpy, tanpa lib tambahan)
# ----------------------------------------------------------------------------

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val.fillna(50)


def macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0):
    mid = sma(series, window)
    std = series.rolling(window=window, min_periods=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()


# ----------------------------------------------------------------------------
# DATA FETCH (di-cache supaya tidak berulang kali hit yfinance)
# ----------------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def fetch_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(how="all")
    return df


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["MA20"] = sma(out["Close"], 20)
    out["MA50"] = sma(out["Close"], 50)
    out["MA200"] = sma(out["Close"], 200)
    out["RSI14"] = rsi(out["Close"], 14)
    macd_line, signal_line, hist = macd(out["Close"])
    out["MACD"] = macd_line
    out["MACD_signal"] = signal_line
    out["MACD_hist"] = hist
    bb_u, bb_m, bb_l = bollinger_bands(out["Close"])
    out["BB_upper"] = bb_u
    out["BB_mid"] = bb_m
    out["BB_lower"] = bb_l
    out["Vol_MA20"] = sma(out["Volume"], 20)
    out["ATR14"] = atr(out, 14)
    return out


# ----------------------------------------------------------------------------
# SCORING / SIGNAL ENGINE (rule-based, transparan & bisa diaudit)
# ----------------------------------------------------------------------------

def score_stock(df: pd.DataFrame) -> dict:
    """Menghasilkan skor -100..100 berdasarkan kombinasi indikator teknikal."""
    if len(df) < 60 or df[["MA50", "RSI14", "MACD"]].iloc[-1].isna().any():
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0
    reasons = []

    # 1) Trend jangka menengah-panjang (MA alignment)
    if pd.notna(last["MA200"]):
        if last["Close"] > last["MA50"] > last["MA200"]:
            score += 20
            reasons.append("Uptrend: Close > MA50 > MA200")
        elif last["Close"] < last["MA50"] < last["MA200"]:
            score -= 20
            reasons.append("Downtrend: Close < MA50 < MA200")
    else:
        if last["Close"] > last["MA50"]:
            score += 10
            reasons.append("Harga di atas MA50")
        else:
            score -= 10
            reasons.append("Harga di bawah MA50")

    # 2) Golden / Death cross MA20 vs MA50 (baru terjadi dlm beberapa hari terakhir)
    cross_window = df.iloc[-6:]
    ma20_above = cross_window["MA20"] > cross_window["MA50"]
    if ma20_above.iloc[-1] and not ma20_above.iloc[0]:
        score += 15
        reasons.append("Golden cross MA20/MA50 baru terjadi")
    elif not ma20_above.iloc[-1] and ma20_above.iloc[0]:
        score -= 15
        reasons.append("Death cross MA20/MA50 baru terjadi")

    # 3) RSI (oversold/overbought)
    if last["RSI14"] < 30:
        score += 15
        reasons.append(f"RSI oversold ({last['RSI14']:.1f})")
    elif last["RSI14"] > 70:
        score -= 15
        reasons.append(f"RSI overbought ({last['RSI14']:.1f})")
    elif 45 <= last["RSI14"] <= 60:
        score += 5
        reasons.append(f"RSI netral-bullish ({last['RSI14']:.1f})")

    # 4) MACD momentum
    if last["MACD"] > last["MACD_signal"] and last["MACD_hist"] > prev["MACD_hist"]:
        score += 15
        reasons.append("MACD bullish & histogram menguat")
    elif last["MACD"] < last["MACD_signal"] and last["MACD_hist"] < prev["MACD_hist"]:
        score -= 15
        reasons.append("MACD bearish & histogram melemah")

    # 5) Volume (indikasi akumulasi/distribusi kasar, proxy "bandar flow")
    if pd.notna(last["Vol_MA20"]) and last["Vol_MA20"] > 0:
        vol_ratio = last["Volume"] / last["Vol_MA20"]
        price_change = last["Close"] - prev["Close"]
        if vol_ratio > 1.5 and price_change > 0:
            score += 10
            reasons.append(f"Volume spike {vol_ratio:.1f}x + harga naik (indikasi akumulasi)")
        elif vol_ratio > 1.5 and price_change < 0:
            score -= 10
            reasons.append(f"Volume spike {vol_ratio:.1f}x + harga turun (indikasi distribusi)")
    else:
        vol_ratio = np.nan

    # 6) Posisi terhadap Bollinger Band
    if pd.notna(last["BB_lower"]) and last["Close"] <= last["BB_lower"] * 1.01:
        score += 10
        reasons.append("Harga dekat/menyentuh Bollinger Band bawah")
    elif pd.notna(last["BB_upper"]) and last["Close"] >= last["BB_upper"] * 0.99:
        score -= 10
        reasons.append("Harga dekat/menyentuh Bollinger Band atas")

    # Klasifikasi sinyal
    if score >= 40:
        signal = "Strong Buy"
    elif score >= 15:
        signal = "Buy"
    elif score > -15:
        signal = "Hold/Watch"
    elif score > -40:
        signal = "Sell"
    else:
        signal = "Strong Sell"

    close = last["Close"]
    atr_val = last["ATR14"] if pd.notna(last["ATR14"]) else close * 0.02
    stop_loss = close - 1.5 * atr_val
    take_profit = close + 2.0 * atr_val
    change_pct = (last["Close"] / prev["Close"] - 1) * 100

    return {
        "score": score,
        "signal": signal,
        "close": close,
        "change_pct": change_pct,
        "rsi": last["RSI14"],
        "vol_ratio": vol_ratio,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "reasons": reasons,
    }


# ----------------------------------------------------------------------------
# UI HELPERS
# ----------------------------------------------------------------------------

SIGNAL_COLOR = {
    "Strong Buy": "#0f9d58",
    "Buy": "#34a853",
    "Hold/Watch": "#f9ab00",
    "Sell": "#e8710a",
    "Strong Sell": "#d93025",
}


PRICE_HOVER = "%{y:,.0f}<extra></extra>"
RATIO_HOVER = "%{y:,.2f}<extra></extra>"


def render_candlestick(df: pd.DataFrame, ticker: str):
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.2, 0.25], vertical_spacing=0.03,
        subplot_titles=(f"{ticker} — Harga & MA/BB", "Volume", "RSI / MACD"),
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20", line=dict(width=1),
                              hovertemplate=PRICE_HOVER), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50", line=dict(width=1),
                              hovertemplate=PRICE_HOVER), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA200"], name="MA200", line=dict(width=1),
                              hovertemplate=PRICE_HOVER), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], name="BB Upper",
                              line=dict(width=1, dash="dot"), opacity=0.5,
                              hovertemplate=PRICE_HOVER), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"], name="BB Lower",
                              line=dict(width=1, dash="dot"), opacity=0.5,
                              fill="tonexty", hovertemplate=PRICE_HOVER), row=1, col=1)

    vol_colors = np.where(df["Close"] >= df["Open"], "#34a853", "#e8710a")
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=vol_colors,
                          hovertemplate="%{y:,.0f}<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Vol_MA20"], name="Vol MA20", line=dict(width=1),
                              hovertemplate="%{y:,.0f}<extra></extra>"), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI14", line=dict(width=1.3, color="#7c4dff"),
                              hovertemplate=RATIO_HOVER), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.4, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.4, row=3, col=1)

    fig.update_layout(height=800, xaxis_rangeslider_visible=False,
                       legend=dict(orientation="h", yanchor="bottom", y=1.02),
                       margin=dict(l=10, r=10, t=40, b=10))
    fig.update_yaxes(tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(tickformat=",.0f", row=2, col=1)
    fig.update_yaxes(tickformat=",.1f", row=3, col=1)
    return fig


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------

def normalize_ticker(t: str) -> str:
    """Tambahkan otomatis .JK jika belum ada suffix bursa (default: IDX)."""
    t = t.strip().upper()
    if "." not in t:
        t = f"{t}.JK"
    return t


st.sidebar.title("⚙️ Pengaturan")
tickers_text = st.sidebar.text_area(
    "Daftar ticker (pisahkan koma). Boleh tanpa .JK, akan ditambahkan otomatis",
    value=", ".join(DEFAULT_TICKERS),
    height=140,
)
tickers = [normalize_ticker(t) for t in tickers_text.split(",") if t.strip()]

# Periode fetch data historis: dibuat cukup panjang (fixed) agar MA50/MA200,
# RSI, MACD dsb tetap akurat -- indikator ini butuh data historis minimal
# 50-200 hari, sehingga tidak bisa dipersingkat jadi 1 minggu/1 bulan tanpa
# merusak perhitungan sinyal.
FETCH_PERIOD = "1y"

# Periode TAMPILAN chart (hanya memotong jumlah hari yang di-plot, tidak
# memengaruhi akurasi perhitungan indikator karena data historis penuh
# tetap diambil di background).
DISPLAY_PERIOD_DAYS = {
    "1 minggu": 5,
    "2 minggu": 10,
    "1 bulan": 22,
    "3 bulan": 66,
    "6 bulan": 130,
    "1 tahun": 260,
}
display_period_label = st.sidebar.selectbox(
    "Periode tampilan chart", list(DISPLAY_PERIOD_DAYS.keys()), index=4
)

st.sidebar.caption(
    "ℹ️ Data historis tetap diambil penuh (1 tahun) di belakang layar agar "
    "MA50/MA200/RSI/MACD akurat. 'Periode tampilan' di atas hanya memperbesar "
    "(zoom) rentang hari yang terlihat di chart, bukan mengurangi data hitung."
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ **Disclaimer**: Aplikasi ini hanya alat bantu analisis teknikal "
    "otomatis, bukan rekomendasi/nasihat investasi. Data dari Yahoo Finance "
    "bisa delay/tidak akurat 100% untuk saham IDX. Selalu cek ulang di "
    "aplikasi resmi sekuritas Anda sebelum eksekusi order, dan gunakan "
    "manajemen risiko sendiri."
)

# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

st.title("📈 IDX Stock Screener & Technical Signal")
st.caption(f"Terakhir dimuat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · "
           f"Sumber data: Yahoo Finance (yfinance)")

tab_screener, tab_chart, tab_flow, tab_guide = st.tabs(
    ["📊 Stock Screener", "📉 Chart Detail", "🌊 Foreign/Bandar Flow", "ℹ️ Panduan"]
)

# ---------------- TAB 1: SCREENER ----------------
with tab_screener:
    st.subheader("Ringkasan Sinyal Semua Saham")
    run = st.button("🔄 Jalankan Screener", type="primary")

    if run or "screener_result" in st.session_state:
        if run:
            rows = []
            progress = st.progress(0.0, text="Mengambil data...")
            for i, tk in enumerate(tickers):
                try:
                    raw = fetch_data(tk, period=FETCH_PERIOD)
                    if raw.empty or len(raw) < 60:
                        continue
                    ind = compute_indicators(raw)
                    result = score_stock(ind)
                    if result is None:
                        continue
                    rows.append({
                        "Ticker": tk,
                        "Sinyal": result["signal"],
                        "Skor": result["score"],
                        "Close": result["close"],
                        "Chg %": result["change_pct"],
                        "RSI14": result["rsi"],
                        "Vol Ratio": result["vol_ratio"],
                        "Stop Loss": result["stop_loss"],
                        "Take Profit": result["take_profit"],
                        "Alasan": " | ".join(result["reasons"]),
                    })
                except Exception as e:
                    st.warning(f"Gagal ambil data {tk}: {e}")
                progress.progress((i + 1) / len(tickers), text=f"Memproses {tk}...")
            progress.empty()
            df_result = pd.DataFrame(rows).sort_values("Skor", ascending=False).reset_index(drop=True)
            st.session_state["screener_result"] = df_result

        df_result = st.session_state["screener_result"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Strong Buy", int((df_result["Sinyal"] == "Strong Buy").sum()))
        c2.metric("Buy", int((df_result["Sinyal"] == "Buy").sum()))
        c3.metric("Hold/Watch", int((df_result["Sinyal"] == "Hold/Watch").sum()))
        c4.metric("Sell/Strong Sell", int(df_result["Sinyal"].isin(["Sell", "Strong Sell"]).sum()))

        def highlight_signal(row):
            color = SIGNAL_COLOR.get(row["Sinyal"], "#ffffff")
            return [f"background-color: {color}22"] * len(row)

        st.dataframe(
            df_result.style.apply(highlight_signal, axis=1).format({
                "Close": "{:,.0f}",
                "Chg %": "{:,.2f}",
                "RSI14": "{:,.1f}",
                "Vol Ratio": "{:,.2f}",
                "Stop Loss": "{:,.0f}",
                "Take Profit": "{:,.0f}",
            }, na_rep="-"),
            use_container_width=True,
            height=560,
        )
        st.caption("Klik header kolom untuk mengurutkan. Buka tab 'Chart Detail' untuk analisis per saham.")
    else:
        st.info("Klik **Jalankan Screener** untuk mengambil data & menghitung sinyal semua ticker di sidebar.")

# ---------------- TAB 2: CHART DETAIL ----------------
with tab_chart:
    st.subheader("Analisis Teknikal Per Saham")
    sel_ticker = st.selectbox("Pilih ticker", tickers)
    if st.button("Muat Chart"):
        with st.spinner(f"Mengambil data {sel_ticker}..."):
            raw = fetch_data(sel_ticker, period=FETCH_PERIOD)
            if raw.empty:
                st.error("Data tidak ditemukan. Cek kembali kode ticker Anda.")
            else:
                ind = compute_indicators(raw)
                result = score_stock(ind)
                if result:
                    color = SIGNAL_COLOR.get(result["signal"], "#333")
                    st.markdown(
                        f"### Sinyal: <span style='color:{color}'>{result['signal']}</span> "
                        f"(Skor: {result['score']})",
                        unsafe_allow_html=True,
                    )
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Close Terakhir", f"{result['close']:,.0f}", f"{result['change_pct']:.2f}%")
                    m2.metric("RSI14", f"{result['rsi']:.1f}")
                    m3.metric("Stop Loss (est.)", f"{result['stop_loss']:,.0f}")
                    m4.metric("Take Profit (est.)", f"{result['take_profit']:,.0f}")
                    with st.expander("Alasan skor teknikal"):
                        for r in result["reasons"]:
                            st.write("• " + r)
                n_days = DISPLAY_PERIOD_DAYS[display_period_label]
                st.plotly_chart(render_candlestick(ind.tail(n_days), sel_ticker), use_container_width=True)

# ---------------- TAB 3: FOREIGN / BANDAR FLOW ----------------
with tab_flow:
    st.subheader("Foreign Flow / Bandar Flow (mode upload data)")
    st.markdown(
        """
Data **foreign flow** dan **bandarmology** (net broker/foreign buy-sell)
**tidak tersedia gratis di yfinance** — data ini biasanya berasal dari IDX
langsung atau platform seperti Stockbit, RTI, atau aplikasi sekuritas Anda.

Untuk melengkapi analisis teknikal di atas, Anda bisa **upload file CSV**
hasil ekspor dari sumber tersebut, dan aplikasi ini akan memvisualisasikan
trennya.

**Format CSV yang diharapkan** (nama kolom bebas mirip ini):
`Date, Ticker, ForeignBuy, ForeignSell` atau `Date, Ticker, NetForeignValue`
        """
    )
    uploaded = st.file_uploader("Upload CSV foreign/bandar flow", type=["csv"])
    if uploaded is not None:
        try:
            flow_df = pd.read_csv(uploaded)
            st.dataframe(flow_df, use_container_width=True)

            cols = [c.lower() for c in flow_df.columns]
            flow_df.columns = cols

            if "netforeignvalue" in cols:
                net_col = "netforeignvalue"
            elif "foreignbuy" in cols and "foreignsell" in cols:
                flow_df["netforeignvalue"] = flow_df["foreignbuy"] - flow_df["foreignsell"]
                net_col = "netforeignvalue"
            else:
                net_col = None

            if net_col and "date" in cols:
                flow_df["date"] = pd.to_datetime(flow_df["date"])
                if "ticker" in cols:
                    pick = st.selectbox("Filter ticker", ["(Semua)"] + sorted(flow_df["ticker"].unique().tolist()))
                    plot_df = flow_df if pick == "(Semua)" else flow_df[flow_df["ticker"] == pick]
                else:
                    plot_df = flow_df
                plot_df = plot_df.sort_values("date")
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=plot_df["date"], y=plot_df[net_col],
                    marker_color=np.where(plot_df[net_col] >= 0, "#0f9d58", "#d93025"),
                    name="Net Foreign Flow",
                ))
                fig.update_layout(title="Net Foreign/Bandar Flow", height=400)
                st.plotly_chart(fig, use_container_width=True)

                cum = plot_df[net_col].cumsum()
                st.line_chart(pd.DataFrame({"Kumulatif Net Flow": cum.values}, index=plot_df["date"]))
            else:
                st.warning("Kolom tidak dikenali. Pastikan ada kolom 'date' dan 'netforeignvalue' "
                           "atau 'foreignbuy' + 'foreignsell'.")
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

# ---------------- TAB 4: PANDUAN ----------------
with tab_guide:
    st.subheader("Cara Pakai & Metodologi")
    st.markdown(
        """
### Metodologi Skor
Skor total (-100 s/d 100) dibentuk dari kombinasi 6 sinyal teknikal:
1. **Trend** — posisi harga vs MA50/MA200
2. **Golden/Death Cross** — persilangan MA20 & MA50
3. **RSI(14)** — kondisi oversold/overbought
4. **MACD** — momentum bullish/bearish
5. **Volume** — proxy kasar akumulasi/distribusi (bukan bandarmology asli)
6. **Bollinger Band** — posisi harga relatif terhadap band

Klasifikasi: Strong Buy (≥40) · Buy (15–39) · Hold/Watch (-14 s/d 14) ·
Sell (-39 s/d -15) · Strong Sell (≤-40)

### Batasan Penting
- **Bukan bandarmology asli**: sinyal volume di atas hanya proxy sederhana,
  bukan data broker summary sesungguhnya.
- **Foreign flow** perlu diupload manual dari sumber IDX/sekuritas Anda
  (lihat tab Foreign/Bandar Flow).
- **Data yfinance** untuk saham IDX kadang delay atau ada gap; selalu
  cross-check harga real-time di aplikasi sekuritas sebelum eksekusi order.
- Ini adalah **alat bantu**, keputusan akhir & risiko tetap di tangan Anda.

### Deploy
- Lokal: `streamlit run app.py`
- Gratis online: push ke GitHub lalu deploy via [share.streamlit.io](https://share.streamlit.io)
        """
    )
