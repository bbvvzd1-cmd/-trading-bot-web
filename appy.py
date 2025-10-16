import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="Crypto Trading Bot",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for better appearance
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .signal-card {
        padding: 1rem;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid;
    }
    .strong-buy {
        border-color: #00ff00;
        background-color: rgba(0, 255, 0, 0.1);
    }
    .moderate-buy {
        border-color: #ffff00;
        background-color: rgba(255, 255, 0, 0.1);
    }
    .weak-buy {
        border-color: #00ffff;
        background-color: rgba(0, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

class WebTradingBot:
    def __init__(self):
        self.exchange = ccxt.binance()
        self.popular_pairs = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
            'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
            'MATIC/USDT', 'LTC/USDT', 'SHIB/USDT', 'PEPE/USDT', 'FLOKI/USDT'
        ]
    
    def get_price_data(self, symbol, timeframe='1m', limit=50):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except:
            return None
    
    def calculate_indicators(self, df):
        try:
            # RSI
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            
            # Moving Averages
            df['ema_fast'] = ta.trend.EMAIndicator(df['close'], window=8).ema_indicator()
            df['ema_slow'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
            
            # Volume
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            return df
        except:
            return None
    
    def generate_signal(self, df, symbol):
        try:
            if df is None or len(df) < 20:
                return None
            
            latest = df.iloc[-1]
            
            # Calculate points
            points = 0
            conditions = []
            
            # RSI condition
            if latest['rsi'] < 30:
                points += 25
                conditions.append("RSI Oversold")
            elif latest['rsi'] < 40:
                points += 15
                conditions.append("RSI Near Oversold")
            
            # Moving average condition
            if latest['ema_fast'] > latest['ema_slow']:
                points += 20
                conditions.append("Uptrend")
            
            # Volume condition
            if latest['volume_ratio'] > 2.0:
                points += 15
                conditions.append("High Volume")
            
            # Price momentum
            price_change = (latest['close'] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
            if price_change > -2:
                points += 10
                conditions.append("Good Momentum")
            
            # Determine signal strength
            if points >= 50:
                if points >= 70:
                    signal_type = "STRONG BUY"
                    signal_class = "strong-buy"
                elif points >= 60:
                    signal_type = "MODERATE BUY"
                    signal_class = "moderate-buy"
                else:
                    signal_type = "WEAK BUY"
                    signal_class = "weak-buy"
                
                signal_data = {
                    'symbol': symbol,
                    'signal': signal_type,
                    'class': signal_class,
                    'confidence': points,
                    'price': round(latest['close'], 6),
                    'rsi': round(latest['rsi'], 1),
                    'volume_ratio': round(latest['volume_ratio'], 1),
                    'conditions': conditions,
                    'timestamp': datetime.now()
                }
                return signal_data
            
            return None
            
        except:
            return None

def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 Web Crypto Trading Bot</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Settings")
    auto_refresh = st.sidebar.checkbox("Auto Refresh Every 60 Seconds", value=True)
    
    if auto_refresh:
        st.sidebar.write("Next refresh in 60 seconds")
    
    # Initialize bot
    bot = WebTradingBot()
    
    # Analysis section
    st.subheader("🔍 Market Analysis")
    
    if st.button("Analyze Now") or auto_refresh:
        with st.spinner("Analyzing 15 popular cryptocurrencies..."):
            signals = []
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, symbol in enumerate(bot.popular_pairs):
                status_text.text(f"Analyzing {symbol}...")
                
                df = bot.get_price_data(symbol)
                if df is not None:
                    df = bot.calculate_indicators(df)
                    signal = bot.generate_signal(df, symbol)
                    if signal:
                        signals.append(signal)
                
                progress_bar.progress((i + 1) / len(bot.popular_pairs))
            
            status_text.text("Analysis complete!")
            
            # Display results
            if signals:
                st.success(f"🎯 Found {len(signals)} Trading Signals!")
                
                # Sort by confidence
                signals.sort(key=lambda x: x['confidence'], reverse=True)
                
                # Display each signal
                for signal in signals:
                    with st.container():
                        st.markdown(f"""
                        <div class="signal-card {signal['class']}">
                            <h3>{signal['symbol']} - {signal['signal']}</h3>
                            <p><strong>Confidence:</strong> {signal['confidence']}% | 
                            <strong>Price:</strong> ${signal['price']} | 
                            <strong>RSI:</strong> {signal['rsi']} | 
                            <strong>Volume:</strong> {signal['volume_ratio']}x</p>
                            <p><strong>Conditions:</strong> {', '.join(signal['conditions'])}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ No strong trading signals found. Waiting for better opportunities...")
            
            # Show last update time
            st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(60)
        st.experimental_rerun()

if __name__ == "__main__":
    main()
