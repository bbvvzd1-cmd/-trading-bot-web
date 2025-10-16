import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import json

# Page configuration
st.set_page_config(
    page_title="Crypto Trading Bot - Auto 15min",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .signal-card {
        padding: 1rem;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid;
        background-color: #f0f2f6;
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
    .countdown {
        font-size: 1.2rem;
        font-weight: bold;
        color: #ff6b6b;
        text-align: center;
        padding: 10px;
        background-color: #2d3436;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

class AutoTradingBot:
    def __init__(self):
        self.popular_pairs = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT',
            'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'FILUSDT'
        ]
        self.analysis_interval = 15  # minutes
        self.last_analysis = None
        self.signals_history = []
    
    def get_binance_data(self, symbol, interval='15m', limit=50):
        """Get 15-minute data from Binance API"""
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            response = requests.get(url, params=params)
            data = response.json()
            
            # Convert to DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            return None
    
    def calculate_rsi(self, prices, window=14):
        """Calculate RSI manually"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return pd.Series([50] * len(prices))
    
    def calculate_ema(self, prices, window):
        """Calculate EMA manually"""
        return prices.ewm(span=window).mean()
    
    def analyze_symbol(self, symbol):
        """Analyze a single symbol with 15min data"""
        try:
            df = self.get_binance_data(symbol, '15m')
            if df is None or len(df) < 20:
                return None
            
            # Calculate indicators
            df['rsi'] = self.calculate_rsi(df['close'])
            df['ema_fast'] = self.calculate_ema(df['close'], 8)
            df['ema_slow'] = self.calculate_ema(df['close'], 21)
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            latest = df.iloc[-1]
            
            # Advanced scoring system
            points = 0
            conditions = []
            
            # RSI conditions (25 points max)
            if latest['rsi'] < 30:
                points += 25
                conditions.append("RSI Oversold (<30)")
            elif latest['rsi'] < 35:
                points += 20
                conditions.append("RSI Near Oversold (30-35)")
            elif latest['rsi'] < 40:
                points += 15
                conditions.append("RSI Low (35-40)")
            
            # Trend conditions (25 points max)
            if latest['ema_fast'] > latest['ema_slow']:
                points += 20
                conditions.append("Uptrend (EMA8 > EMA21)")
                # Additional points for strong trend
                trend_strength = (latest['ema_fast'] - latest['ema_slow']) / latest['ema_slow'] * 100
                if trend_strength > 1:
                    points += 5
                    conditions.append("Strong Uptrend")
            
            # Volume conditions (20 points max)
            if latest['volume_ratio'] > 3.0:
                points += 20
                conditions.append("Very High Volume (3x+)")
            elif latest['volume_ratio'] > 2.0:
                points += 15
                conditions.append("High Volume (2x+)")
            elif latest['volume_ratio'] > 1.5:
                points += 10
                conditions.append("Above Average Volume (1.5x+)")
            
            # Price momentum (15 points max)
            price_change_15m = (latest['close'] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
            price_change_1h = (latest['close'] - df['close'].iloc[-4]) / df['close'].iloc[-4] * 100
            
            if price_change_15m > 1:
                points += 10
                conditions.append("Strong 15m Momentum")
            elif price_change_15m > 0:
                points += 5
                conditions.append("Positive 15m Momentum")
            
            if price_change_1h > 2:
                points += 5
                conditions.append("Strong 1h Trend")
            
            # Support/Resistance (15 points max)
            support_level = df['low'].rolling(10).min().iloc[-1]
            resistance_level = df['high'].rolling(10).max().iloc[-1]
            current_to_support = (latest['close'] - support_level) / support_level * 100
            
            if current_to_support < 2:
                points += 15
                conditions.append("Near Support Level")
            elif current_to_support < 5:
                points += 10
                conditions.append("Close to Support")
            
            # Determine signal strength
            if points >= 60:
                if points >= 80:
                    signal_type = "STRONG BUY 🟢"
                    signal_class = "strong-buy"
                elif points >= 70:
                    signal_type = "MODERATE BUY 🟡"
                    signal_class = "moderate-buy"
                else:
                    signal_type = "WEAK BUY 🔵"
                    signal_class = "weak-buy"
                
                return {
                    'symbol': symbol,
                    'signal': signal_type,
                    'class': signal_class,
                    'confidence': points,
                    'price': round(latest['close'], 4),
                    'rsi': round(latest['rsi'], 1),
                    'volume_ratio': round(latest['volume_ratio'], 1),
                    'price_change_15m': round(price_change_15m, 2),
                    'price_change_1h': round(price_change_1h, 2),
                    'conditions': conditions,
                    'timestamp': datetime.now()
                }
            
            return None
            
        except Exception as e:
            return None
    
    def should_analyze(self):
        """Check if it's time for analysis"""
        if self.last_analysis is None:
            return True
        
        time_since_last = (datetime.now() - self.last_analysis).total_seconds() / 60
        return time_since_last >= self.analysis_interval
    
    def get_next_analysis_time(self):
        """Get time until next analysis"""
        if self.last_analysis is None:
            return 0
        
        next_analysis = self.last_analysis + timedelta(minutes=self.analysis_interval)
        time_until = (next_analysis - datetime.now()).total_seconds()
        return max(0, time_until)

def main():
    st.markdown('<h1 class="main-header">🤖 Auto Crypto Trading Bot (15min)</h1>', unsafe_allow_html=True)
    
    st.write("""
    **Automated bot that analyzes cryptocurrencies every 15 minutes** using 15-minute interval data.
    More reliable signals with reduced market noise.
    """)
    
    # Initialize bot
    if 'bot' not in st.session_state:
        st.session_state.bot = AutoTradingBot()
        st.session_state.auto_refresh = True
    
    bot = st.session_state.bot
    
    # Sidebar
    with st.sidebar:
        st.subheader("⚙️ Auto Settings")
        st.session_state.auto_refresh = st.checkbox("Auto Refresh", value=True)
        
        st.subheader("📈 Next Analysis")
        time_until = bot.get_next_analysis_time()
        minutes = int(time_until // 60)
        seconds = int(time_until % 60)
        
        if bot.last_analysis:
            st.write(f"Last: {bot.last_analysis.strftime('%H:%M:%S')}")
            st.write(f"Next: in {minutes:02d}:{seconds:02d}")
        else:
            st.write("Ready for first analysis!")
        
        st.subheader("📊 Statistics")
        if bot.signals_history:
            total_signals = len(bot.signals_history)
            strong_signals = len([s for s in bot.signals_history if s['confidence'] >= 80])
            st.write(f"Total Signals: {total_signals}")
            st.write(f"Strong Signals: {strong_signals}")
    
    # Main content
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 Live Market Analysis")
        
        # Auto-analysis logic
        if bot.should_analyze() and st.session_state.auto_refresh:
            with st.spinner(f"Auto-analyzing {len(bot.popular_pairs)} cryptocurrencies..."):
                signals = []
                
                # Progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, symbol in enumerate(bot.popular_pairs):
                    status_text.text(f"Analyzing {symbol}...")
                    signal = bot.analyze_symbol(symbol)
                    if signal:
                        signals.append(signal)
                    progress_bar.progress((i + 1) / len(bot.popular_pairs))
                    time.sleep(0.3)  # Rate limiting
                
                bot.last_analysis = datetime.now()
                bot.signals_history.extend(signals)
                status_text.text("Auto-analysis complete!")
                
                # Display results
                if signals:
                    st.success(f"🎯 Auto-detected {len(signals)} Trading Signals!")
                    st.write("---")
                    
                    # Sort by confidence
                    signals.sort(key=lambda x: x['confidence'], reverse=True)
                    
                    for signal in signals:
                        with st.expander(f"{signal['symbol']} - {signal['signal']} ({signal['confidence']}%)", expanded=True):
                            st.markdown(f"""
                            <div class="signal-card {signal['class']}">
                                <h4>📊 Analysis Details:</h4>
                                <p><b>Price:</b> ${signal['price']} | 
                                <b>RSI:</b> {signal['rsi']} | 
                                <b>Volume:</b> {signal['volume_ratio']}x</p>
                                <p><b>15m Change:</b> {signal['price_change_15m']}% | 
                                <b>1h Change:</b> {signal['price_change_1h']}%</p>
                                <p><b>Conditions Met:</b> {', '.join(signal['conditions'])}</p>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("""
                    🤖 **No strong signals detected in this cycle.**
                    
                    *This is normal!* The bot is waiting for optimal conditions:
                    - RSI oversold levels
                    - Strong volume confirmation  
                    - Clear uptrend signals
                    - Support level bounces
                    """)
        
        # Manual analysis button
        if st.button("🔍 Manual Analysis Now", type="secondary"):
            with st.spinner("Running manual analysis..."):
                signals = []
                for symbol in bot.popular_pairs:
                    signal = bot.analyze_symbol(symbol)
                    if signal:
                        signals.append(signal)
                
                if signals:
                    st.success(f"Manual analysis found {len(signals)} signals!")
                    # Display would go here...
    
    with col2:
        st.subheader("🎯 Supported Coins")
        for coin in bot.popular_pairs:
            st.write(f"• {coin}")
        
        st.subheader("📋 Signal Criteria")
        st.info("""
        **Strong Buy (80+ points):**
        - RSI < 30
        - Strong uptrend
        - High volume
        - Near support
        
        **Moderate Buy (70-79):**
        - RSI 30-35  
        - Good volume
        - Positive momentum
        """)
    
    # Countdown and auto-refresh
    if st.session_state.auto_refresh:
        time_until = bot.get_next_analysis_time()
        if time_until > 0:
            minutes = int(time_until // 60)
            seconds = int(time_until % 60)
            st.markdown(f'<div class="countdown">🕒 Next auto-analysis in: {minutes:02d}:{seconds:02d}</div>', unsafe_allow_html=True)
        
        # Auto-refresh the app
        time.sleep(1)
        st.rerun()
    
    # Footer
    st.write("---")
    st.write(f"🤖 Bot Status: {'🟢 RUNNING' if st.session_state.auto_refresh else '⏸️ PAUSED'} | Last update: {datetime.now().strftime('%H:%M:%S')}")
    st.caption("15-minute interval analysis | Educational purposes only")

if __name__ == "__main__":
    main()
