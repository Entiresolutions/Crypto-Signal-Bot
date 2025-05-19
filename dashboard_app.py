import streamlit as st
import pandas as pd
import os
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import plotly.express as px
from binance.client import Client
import datetime

# Binance public API (no key needed for public data)
client = Client()

# Auto-refresh every 30 sec
st_autorefresh(interval=30000, key="data_refresh")

st.title("📊 Crypto Signal Log Dashboard")

log_file = "signals_log.txt"

def get_binance_ohlcv(symbol, interval, limit=50):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    data = {
        "Time": [datetime.datetime.fromtimestamp(x[0] / 1000) for x in klines],
        "Open": [float(x[1]) for x in klines],
        "High": [float(x[2]) for x in klines],
        "Low": [float(x[3]) for x in klines],
        "Close": [float(x[4]) for x in klines],
    }
    return pd.DataFrame(data)

if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf-8") as f:
        logs = f.readlines()

    signals = []
    current_signal = {}

    for line in logs:
        if "ALERT" in line and "⚡" in line:
            if current_signal:
                signals.append(current_signal)
                current_signal = {}

            try:
                parts = line.split("⚡")[1].split("ALERT")
                if len(parts) < 2:
                    continue
                symbol_tf = parts[0].strip()
                current_signal["Time"] = line.split("]")[0][1:]
                current_signal["Pair / Timeframe"] = symbol_tf
                current_signal["Type"] = "Buy"
            except Exception:
                continue

        elif "Current Price:" in line:
            current_signal["Current Price"] = line.split(":")[1].strip()
        elif "ATR:" in line:
            current_signal["ATR"] = line.split(":")[1].strip()
        elif "Buy Price:" in line:
            current_signal["Buy Price"] = line.split(":")[1].strip()
        elif "Take Profit:" in line:
            current_signal["Take Profit"] = line.split(":")[1].strip()
        elif "Stop Loss:" in line:
            current_signal["Stop Loss"] = line.split(":")[1].strip()

    if current_signal:
        signals.append(current_signal)

    if signals:
        df = pd.DataFrame(signals)

        # Add Profit % column
        if "Buy Price" in df.columns and "Take Profit" in df.columns:
            df["Profit %"] = (
                (pd.to_numeric(df["Take Profit"], errors="coerce") - pd.to_numeric(df["Buy Price"], errors="coerce"))
                / pd.to_numeric(df["Buy Price"], errors="coerce") * 100
            ).round(2)

        # Moving ticker for latest signals (last 10)
        latest_signals_text = " | ".join(
            f"{sig['Pair / Timeframe']}: Buy {sig.get('Buy Price', '')} | TP: {sig.get('Take Profit', '')} | SL: {sig.get('Stop Loss', '')}"
            for sig in signals[-10:]
        )

        ticker_html = f"""
        <div style="background-color: #f5f5f5; padding: 8px; overflow: hidden; white-space: nowrap;">
            <marquee behavior="scroll" direction="left" scrollamount="5" style="color: black; font-weight: bold; font-size: 16px;">
                📊 {latest_signals_text}
            </marquee>
        </div>
        """

        st.markdown(ticker_html, unsafe_allow_html=True)

        # Ticker for Take Profit hits
        tp_hits = [sig for sig in signals if sig.get("Buy Price") == sig.get("Take Profit")]

        if tp_hits:
            tp_hits_text = " | ".join(
                f"🎯 {sig['Pair / Timeframe']} TP Hit at {sig.get('Take Profit', '')}"
                for sig in tp_hits
            )

            tp_ticker_html = f"""
            <div style="background-color: #ffeeba; padding: 8px; overflow: hidden; white-space: nowrap;">
                <marquee behavior="scroll" direction="left" scrollamount="6" style="color: black; font-weight: bold; font-size: 16px;">
                    {tp_hits_text}
                </marquee>
            </div>
            """

            st.markdown(tp_ticker_html, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color: #ffeeba; padding: 8px; overflow: hidden; white-space: nowrap;">
                <marquee behavior="scroll" direction="left" scrollamount="6" style="color: black; font-weight: bold; font-size: 16px;">
                    No Take Profit hits yet.
                </marquee>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("📈 Live Signals Table")

        def color_signal(val):
            if val == "Buy":
                return "color: green; font-weight: bold"
            elif val == "Sell":
                return "color: red; font-weight: bold"
            return ""

        styled_df = df.style.applymap(color_signal, subset=["Type"])
        st.dataframe(styled_df, use_container_width=True, height=500)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="signals_log.csv",
            mime="text/csv",
        )
                # 📊 Quotex Signals Table
        st.subheader("📈 Quotex Signals Table")

        quotex_signals = []
        for line in logs:
            if "QUOTEX ALERT" in line and "⚡" in line:
                try:
                    parts = line.split("⚡")[1].split("QUOTEX ALERT")
                    if len(parts) < 2:
                        continue
                    symbol_tf = parts[0].strip()
                    signal_time = line.split("]")[0][1:]

                    quotex_signal = {
                        "Time": signal_time,
                        "Pair / Timeframe": symbol_tf,
                        "Type": "Buy"
                    }

                    # Check for extra details in following lines (like Current Price, TP, SL)
                    index = logs.index(line)
                    for extra_line in logs[index+1:index+6]:  # check next 5 lines
                        if "Current Price:" in extra_line:
                            quotex_signal["Current Price"] = extra_line.split(":")[1].strip()
                        elif "Take Profit:" in extra_line:
                            quotex_signal["Take Profit"] = extra_line.split(":")[1].strip()
                        elif "Stop Loss:" in extra_line:
                            quotex_signal["Stop Loss"] = extra_line.split(":")[1].strip()

                    quotex_signals.append(quotex_signal)
                except Exception:
                    continue

        if quotex_signals:
            quotex_df = pd.DataFrame(quotex_signals)

            def color_quotex(val):
                if val == "Buy":
                    return "color: green; font-weight: bold"
                elif val == "Sell":
                    return "color: red; font-weight: bold"
                return ""

            styled_quotex_df = quotex_df.style.applymap(color_quotex, subset=["Type"])
            st.dataframe(styled_quotex_df, use_container_width=True, height=400)

            csv_quotex = quotex_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Quotex Signals as CSV",
                data=csv_quotex,
                file_name="quotex_signals_log.csv",
                mime="text/csv",
            )
        else:
            st.info("No Quotex signals found yet.")


        st.subheader("📊 Live Binance Candlestick Chart")

        latest_signal = df.iloc[-1]
        selected_pair = latest_signal["Pair / Timeframe"]

        st.info(f"Showing chart for: **{selected_pair}**")

        selected_timeframe = st.selectbox(
            "Select Timeframe", ["15m", "1h", "4h"]
        )

        interval_map = {
            "15m": Client.KLINE_INTERVAL_15MINUTE,
            "1h": Client.KLINE_INTERVAL_1HOUR,
            "4h": Client.KLINE_INTERVAL_4HOUR
        }

        binance_symbol = selected_pair.split(" ")[0].replace("/", "")
        interval = interval_map[selected_timeframe]

        try:
            candle_data = get_binance_ohlcv(binance_symbol, interval)

            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=candle_data["Time"],
                        open=candle_data["Open"],
                        high=candle_data["High"],
                        low=candle_data["Low"],
                        close=candle_data["Close"],
                    )
                ]
            )

            fig.update_layout(
                title=f"{selected_pair} {selected_timeframe} Live Candlestick",
                xaxis_title="Time",
                yaxis_title="Price (USDT)",
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error fetching Binance data: {e}")

        st.subheader("📈 Profit % History")

        profit_df = df[["Time", "Profit %"]].dropna()
        profit_df["Time"] = pd.to_datetime(profit_df["Time"])

        profit_fig = px.line(
            profit_df,
            x="Time",
            y="Profit %",
            markers=True,
            title="Profit % Over Time"
        )

        profit_fig.update_layout(template="plotly_dark")
        st.plotly_chart(profit_fig, use_container_width=True)

        st.subheader("📊 Signal Count by Pair / Timeframe")

        signal_count = df["Pair / Timeframe"].value_counts().reset_index()
        signal_count.columns = ["Pair / Timeframe", "Count"]

        count_fig = px.bar(
            signal_count,
            x="Pair / Timeframe",
            y="Count",
            color="Pair / Timeframe",
            text="Count",
            title="Signal Frequency by Pair / Timeframe"
        )

        count_fig.update_layout(template="plotly_dark", xaxis_tickangle=-45)
        st.plotly_chart(count_fig, use_container_width=True)

    else:
        st.warning("No valid signal logs found yet.")

else:
    st.error("No signal log file found. Please run your bot first.")
