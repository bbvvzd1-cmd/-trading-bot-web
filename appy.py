import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import requests
import json

# Page configuration
st.set_page_config(
    page_title="Crypto Trading Bot",
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
    }
    .moderate-buy {
        border-color: #ffff00;
    }
    .weak-buy {
        border-color: #00ffff;
    }
</style>
""", unsafe_allow_html=True)

class SimpleTradingBot:
    def __init__(self):
        self.popular_pairs = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT'
        ]
    
    def get_binance_data(self, symbol, interval='1m', limit=50):
        """Get data from Binance API without ccxt"""
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
            st.warning(f"Could not fetch data for {symbol}")
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
            return pd.Series([50] * len(prices))  # Default value
    
    def calculate_ema(self, prices, window):
        """Calculate EMA manually"""
        return prices.ewm(span=window).mean()
    
    def analyze_symbol(self, symbol):
        """Analyze a single symbol"""
        try:
            df = self.get_binance_data(symbol)
            if df is None or len(df) < 20:
                return None
            
            # Calculate indicators manually
            df['rsi'] = self.calculate_rsi(df['close'])
            df['ema_fast'] = self.calculate_ema(df['close'], 8)
            df['ema_slow'] = self.calculate_ema(df['close'], 21)
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            latest = df.iloc[-1]
            
            # Calculate points
            points = 0
            conditions = []
            
            # RSI conditions
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
            price_change = (latest['close'] - df['close'].iloc[-10]) / df['close'].iloc[-10] * 100
            if price_change > -3:
                points += 10
                conditions.append("Good Momentum")
            
            # Determine signal
            if points >= 50:
                if points >= 70:
                    signal_type = "STRONG BUY 🟢"
                    signal_class = "strong-buy"
                elif points >= 60:
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
                    'conditions': conditions
                }
            
            return None
            
        except Exception as e:
            return None

def main():
    st.markdown('<h1 class="main-header">🤖 Simple Crypto Trading Bot</h1>', unsafe_allow_html=True)
    
    st.write("""
    This bot analyzes popular cryptocurrencies using Binance data and provides trading signals 
    based on RSI, moving averages, and volume analysis.
    """)
    
    # Initialize bot
    bot = SimpleTradingBot()
    
    # Analysis section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 Market Analysis")
        
        if st.button("🚀 Analyze Market Now", type="primary"):
            with st.spinner("Analyzing 10 popular cryptocurrencies..."):
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
                    time.sleep(0.5)  # Be nice to the API
                
                status_text.text("Analysis complete!")
                
                # Display results
                if signals:
                    st.success(f"🎯 Found {len(signals)} Trading Signals!")
                    st.write("---")
                    
                    # Sort by confidence
                    signals.sort(key=lambda x: x['confidence'], reverse=True)
                    
                    for signal in signals:
                        st.markdown(f"""
                        <div class="signal-card {signal['class']}">
                            <h3>{signal['symbol']}</h3>
                            <h4>{signal['signal']}</h4>
                            <p><b>Confidence:</b> {signal['confidence']}% | 
                            <b>Price:</b> ${signal['price']} | 
                            <b>RSI:</b> {signal['rsi']} | 
                            <b>Volume:</b> {signal['volume_ratio']}x</p>
                            <p><b>Conditions:</b> {', '.join(signal['conditions'])}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("""
                    ⚠️ No strong trading signals found at the moment.
                    
                    **This is normal!** The bot only shows signals when conditions are favorable.
                    Try again in a few minutes when market conditions change.
                    """)
    
    with col2:
        st.subheader("⚙️ Settings")
        st.info("""
        **How it works:**
        - Analyzes RSI (Oversold/Bought)
        - Checks trend direction
        - Monitors trading volume
        - Combines factors for confidence score
        """)
        
        st.write("**Supported Coins:**")
        for coin in bot.popular_pairs:
            st.write(f"• {coin}")
    
    # Footer
    st.write("---")
    st.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("Note: This is for educational purposes only. Always do your own research.")

if __name__ == "__main__":
    main()
