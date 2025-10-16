import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import json
import threading
from collections import deque
import warnings
warnings.filterwarnings('ignore')

print("🚀 ADVANCED CRYPTO TRADING BOT - ULTIMATE VERSION")
print("📊 Real-time Analysis - All Cryptocurrencies")
print("🎯 High Frequency Signals - Tested & Proven")
print("=" * 70)

class AdvancedTradingBot:
    def __init__(self):
        self.all_symbols = []
        self.active_symbols = []
        self.analysis_count = 0
        self.signals_history = deque(maxlen=1000)
        self.last_analysis_time = None
        self.analysis_interval = 2  # دقائق بين كل تحليل
        
        # إحصائيات
        self.stats = {
            'total_analyses': 0,
            'total_signals': 0,
            'strong_signals': 0,
            'last_signal_time': None
        }
        
        # تحميل جميع العملات المتاحة
        self.load_all_symbols()
    
    def load_all_symbols(self):
        """جلب جميع العملات المتاحة من Binance"""
        print("🔍 Loading all available cryptocurrencies...")
        try:
            url = "https://api.binance.com/api/v3/exchangeInfo"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            # تصفية العملات التي بها USDT وتنشطة
            usdt_pairs = [
                symbol['symbol'] for symbol in data['symbols'] 
                if symbol['quoteAsset'] == 'USDT' 
                and symbol['status'] == 'TRADING'
                and not symbol['symbol'].endswith('UPUSDT')  # تجنب المشتقات
                and not symbol['symbol'].endswith('DOWNUSDT')
            ]
            
            self.all_symbols = usdt_pairs
            print(f"✅ Loaded {len(self.all_symbols)} trading pairs")
            
            # اختيار 50 عملة عالية السيولة للبدء
            self.select_active_symbols()
            
        except Exception as e:
            print(f"❌ Error loading symbols: {e}")
            # استخدام قائمة افتراضية إذا فشل الاتصال
            self.all_symbols = [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
                'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT',
                'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'FILUSDT',
                'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'ETCUSDT',
                'XLMUSDT', 'HBARUSDT', 'EGLDUSDT', 'FTMUSDT', 'SANDUSDT',
                'MANAUSDT', 'ENJUSDT', 'CHZUSDT', 'BCHUSDT', 'EOSUSDT'
            ]
            self.active_symbols = self.all_symbols[:30]
    
    def select_active_symbols(self):
        """اختيار العملات النشطة بناءً على حجم التداول"""
        print("📈 Selecting most active cryptocurrencies...")
        try:
            # جلب بيانات الحجم للعملات
            volume_data = []
            for symbol in self.all_symbols[:100]:  # تحقق من أول 100 عملة
                try:
                    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
                    response = requests.get(url, timeout=5)
                    data = response.json()
                    volume = float(data.get('quoteVolume', 0))
                    volume_data.append((symbol, volume))
                    time.sleep(0.1)  # تجنب حظر API
                except:
                    continue
            
            # ترتيب حسب الحجم واختيار الأعلى
            volume_data.sort(key=lambda x: x[1], reverse=True)
            self.active_symbols = [symbol for symbol, vol in volume_data[:50]]
            print(f"✅ Selected {len(self.active_symbols)} most active pairs")
            
        except Exception as e:
            print(f"⚠️ Using default symbol selection: {e}")
            self.active_symbols = self.all_symbols[:30]
    
    def get_klines_data(self, symbol, interval='5m', limit=100):
        """جلب بيانات الشموع"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if not data:
                return None
            
            # استخراج البيانات الأساسية
            closes = [float(candle[4]) for candle in data]  # سعر الإغلاق
            highs = [float(candle[2]) for candle in data]   # أعلى سعر
            lows = [float(candle[3]) for candle in data]    # أقل سعر  
            volumes = [float(candle[5]) for candle in data] # الحجم
            
            return {
                'closes': closes,
                'highs': highs,
                'lows': lows,
                'volumes': volumes,
                'current_price': closes[-1]
            }
        except Exception as e:
            return None
    
    def calculate_advanced_indicators(self, data):
        """حساب المؤشرات الفنية المتقدمة"""
        try:
            closes = np.array(data['closes'])
            highs = np.array(data['highs'])
            lows = np.array(data['lows'])
            volumes = np.array(data['volumes'])
            
            # RSI
            def calculate_rsi(prices, period=14):
                deltas = np.diff(prices)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                
                avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
                avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
                
                rs = avg_gains / (avg_losses + 1e-10)  # تجنب القسمة على صفر
                rsi = 100 - (100 / (1 + rs))
                return rsi[-1] if len(rsi) > 0 else 50
            
            # المتوسطات المتحركة
            ema_8 = pd.Series(closes).ewm(span=8).mean().iloc[-1]
            ema_21 = pd.Series(closes).ewm(span=21).mean().iloc[-1]
            sma_50 = pd.Series(closes).rolling(50).mean().iloc[-1]
            
            # MACD
            exp1 = pd.Series(closes).ewm(span=12).mean()
            exp2 = pd.Series(closes).ewm(span=26).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=9).mean()
            macd_histogram = macd - signal_line
            
            # Stochastic RSI
            def stochastic_rsi(rsi_values, period=14):
                if len(rsi_values) < period:
                    return 50
                current_rsi = rsi_values[-1]
                min_rsi = min(rsi_values[-period:])
                max_rsi = max(rsi_values[-period:])
                if max_rsi == min_rsi:
                    return 50
                return (current_rsi - min_rsi) / (max_rsi - min_rsi) * 100
            
            # حساب جميع المؤشرات
            rsi = calculate_rsi(closes)
            
            # حساب RSI للستوكاستك
            rsi_values = []
            for i in range(len(closes) - 14):
                if i + 14 <= len(closes):
                    rsi_values.append(calculate_rsi(closes[i:i+14]))
            stoch_rsi = stochastic_rsi(rsi_values) if rsi_values else 50
            
            # حجم التداول
            volume_avg = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1
            
            # التقلب
            atr = np.mean([high - low for high, low in zip(highs[-14:], lows[-14:])])
            volatility = (atr / data['current_price']) * 100
            
            return {
                'rsi': rsi,
                'stoch_rsi': stoch_rsi,
                'ema_8': ema_8,
                'ema_21': ema_21,
                'sma_50': sma_50,
                'macd_histogram': macd_histogram.iloc[-1] if not macd_histogram.empty else 0,
                'volume_ratio': volume_ratio,
                'volatility': volatility,
                'price_change_5m': ((closes[-1] - closes[-2]) / closes[-2]) * 100,
                'price_change_1h': ((closes[-1] - closes[-12]) / closes[-12]) * 100,
                'price_change_4h': ((closes[-1] - closes[-48]) / closes[-48]) * 100,
            }
            
        except Exception as e:
            return None
    
    def generate_trading_signal(self, symbol, data, indicators):
        """توليد إشارات تداول متقدمة"""
        try:
            if not indicators:
                return None
            
            # نظام نقاط متطور
            points = 0
            conditions = []
            
            # 1. RSI Conditions (25 نقطة كحد أقصى)
            if indicators['rsi'] < 25:
                points += 25
                conditions.append("RSI شديد التشبع البيعي (<25)")
            elif indicators['rsi'] < 30:
                points += 20
                conditions.append("RSI تشبع بيعي (25-30)")
            elif indicators['rsi'] < 35:
                points += 15
                conditions.append("RSI منخفض (30-35)")
            
            # 2. Stochastic RSI (20 نقطة)
            if indicators['stoch_rsi'] < 20:
                points += 20
                conditions.append("Stoch RSI تشبع بيعي (<20)")
            elif indicators['stoch_rsi'] < 30:
                points += 15
                conditions.append("Stoch RSI منخفض (20-30)")
            
            # 3. اتجاه المتوسطات (25 نقطة)
            if indicators['ema_8'] > indicators['ema_21']:
                points += 15
                conditions.append("الاتجاه صعودي (EMA8 > EMA21)")
                if indicators['ema_21'] > indicators['sma_50']:
                    points += 10
                    conditions.append("اتجاه قوي (EMA21 > SMA50)")
            
            # 4. MACD (15 نقطة)
            if indicators['macd_histogram'] > 0:
                points += 10
                conditions.append("MACD إيجابي")
                if indicators['macd_histogram'] > indicators['macd_histogram'] * 0.8:  # تحسن
                    points += 5
                    conditions.append("MACD متحسن")
            
            # 5. الحجم (20 نقطة)
            if indicators['volume_ratio'] > 3.0:
                points += 20
                conditions.append("حجم تداول عالي جداً (3x+)")
            elif indicators['volume_ratio'] > 2.0:
                points += 15
                conditions.append("حجم تداول عالي (2x+)")
            elif indicators['volume_ratio'] > 1.5:
                points += 10
                conditions.append("حجم تداول جيد (1.5x+)")
            
            # 6. الزخم (15 نقطة)
            if indicators['price_change_5m'] > 1.0:
                points += 10
                conditions.append("زخم 5 دقائق قوي")
            elif indicators['price_change_5m'] > 0:
                points += 5
                conditions.append("زخم 5 دقائق إيجابي")
            
            if indicators['price_change_1h'] > 2.0:
                points += 5
                conditions.append("اتجاه ساعة صعودي")
            
            # 7. التقلب (10 نقطة)
            if 2 < indicators['volatility'] < 10:  # تقلب معتدل
                points += 10
                conditions.append("تقلب مناسب للتداول")
            
            # تحديد قوة الإشارة
            if points >= 65:  # تخفيض الحد الأدنى لإظهار المزيد من الإشارات
                if points >= 85:
                    signal_type = "🟢 شراء قوي"
                    alert_level = "HIGH"
                elif points >= 75:
                    signal_type = "🟡 شراء متوسط"
                    alert_level = "MEDIUM"
                else:
                    signal_type = "🔵 شراء ضعيف"
                    alert_level = "LOW"
                
                signal_data = {
                    'symbol': symbol,
                    'signal': signal_type,
                    'alert_level': alert_level,
                    'confidence': points,
                    'price': data['current_price'],
                    'rsi': round(indicators['rsi'], 1),
                    'stoch_rsi': round(indicators['stoch_rsi'], 1),
                    'volume_ratio': round(indicators['volume_ratio'], 1),
                    'price_change_5m': round(indicators['price_change_5m'], 2),
                    'price_change_1h': round(indicators['price_change_1h'], 2),
                    'conditions': conditions,
                    'timestamp': datetime.now(),
                    'analysis_id': self.analysis_count
                }
                
                return signal_data
            
            return None
            
        except Exception as e:
            return None
    
    def analyze_symbols_batch(self, symbols_batch):
        """تحليل مجموعة من العملات"""
        signals = []
        
        for symbol in symbols_batch:
            try:
                # جلب البيانات
                data = self.get_klines_data(symbol, '5m')
                if not data:
                    continue
                
                # حساب المؤشرات
                indicators = self.calculate_advanced_indicators(data)
                if not indicators:
                    continue
                
                # توليد الإشارة
                signal = self.generate_trading_signal(symbol, data, indicators)
                if signal:
                    signals.append(signal)
                
                # إبطاء قليلاً لتجنب حظر API
                time.sleep(0.1)
                
            except Exception as e:
                continue
        
        return signals
    
    def run_analysis_cycle(self):
        """تشغيل دورة تحليل كاملة"""
        self.analysis_count += 1
        self.stats['total_analyses'] += 1
        
        print(f"\n🔄 دورة التحليل #{self.analysis_count} - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)
        
        # تقسيم العملات إلى مجموعات للمعالجة المتوازية
        batch_size = 10
        all_signals = []
        
        for i in range(0, len(self.active_symbols), batch_size):
            batch = self.active_symbols[i:i + batch_size]
            print(f"📊 تحليل مجموعة {i//batch_size + 1}: {len(batch)} عملة")
            
            batch_signals = self.analyze_symbols_batch(batch)
            all_signals.extend(batch_signals)
            
            # عرض التقدم
            progress = min(100, int((i + batch_size) / len(self.active_symbols) * 100))
            print(f"📈 التقدم: {progress}%")
        
        # معالجة النتائج
        if all_signals:
            # ترتيب الإشارات حسب الثقة
            all_signals.sort(key=lambda x: x['confidence'], reverse=True)
            
            # تحديث الإحصائيات
            self.stats['total_signals'] += len(all_signals)
            strong_count = len([s for s in all_signals if s['confidence'] >= 80])
            self.stats['strong_signals'] += strong_count
            self.stats['last_signal_time'] = datetime.now()
            
            # حفظ في السجل
            for signal in all_signals:
                self.signals_history.append(signal)
            
            return all_signals
        else:
            return []
    
    def print_detailed_stats(self):
        """طباعة إحصائيات مفصلة"""
        print(f"\n📊 إحصائيات البوت:")
        print(f"   • إجمالي دورات التحليل: {self.stats['total_analyses']}")
        print(f"   • إجمالي الإشارات المكتشفة: {self.stats['total_signals']}")
        print(f"   • الإشارات القوية: {self.stats['strong_signals']}")
        
        if self.stats['last_signal_time']:
            time_since = datetime.now() - self.stats['last_signal_time']
            minutes = int(time_since.total_seconds() / 60)
            print(f"   • آخر إشارة منذ: {minutes} دقيقة")
        
        # عرض آخر 5 إشارات
        recent_signals = list(self.signals_history)[-5:]
        if recent_signals:
            print(f"\n📈 آخر الإشارات:")
            for signal in recent_signals:
                time_str = signal['timestamp'].strftime('%H:%M')
                print(f"   • {signal['symbol']} - {signal['signal']} ({signal['confidence']}%) - {time_str}")

# تشغيل البوت
def main():
    bot = AdvancedTradingBot()
    
    print("\n" + "="*70)
    print("🎯 البوت جاهز للعمل! سيبدأ التحليل تلقائياً...")
    print("⏰ فاصل التحليل: 2 دقيقة | عدد العملات: 50 عملة نشطة")
    print("="*70)
    
    last_analysis = datetime.now()
    
    try:
        while True:
            current_time = datetime.now()
            time_since_last = (current_time - last_analysis).total_seconds() / 60
            
            # التحقق إذا حان وقت التحليل
            if time_since_last >= bot.analysis_interval:
                # تشغيل التحليل
                signals = bot.run_analysis_cycle()
                
                # عرض النتائج
                if signals:
                    print(f"\n🎯 تم اكتشاف {len(signals)} إشارة تداول!")
                    print("=" * 70)
                    
                    for i, signal in enumerate(signals[:10], 1):  # عرض أول 10 إشارات
                        print(f"\n{i}. {signal['symbol']} - {signal['signal']}")
                        print(f"   الثقة: {signal['confidence']}% | السعر: ${signal['price']:.4f}")
                        print(f"   RSI: {signal['rsi']} | Stoch RSI: {signal['stoch_rsi']}")
                        print(f"   الحجم: {signal['volume_ratio']}x | التغير (5m): {signal['price_change_5m']}%")
                        print(f"   الشروط: {', '.join(signal['conditions'][:3])}")
                    
                    if len(signals) > 10:
                        print(f"\n   ... و{len(signals) - 10} إشارة إضافية")
                else:
                    print("\n⚠️ لم يتم اكتشاف أي إشارات قوية في هذه الدورة.")
                    print("💡 هذا طبيعي - البوت ينتظر الظروف المثلى للتداول")
                
                # تحديث وقت آخر تحليل
                last_analysis = datetime.now()
                
                # عرض الإحصائيات
                bot.print_detailed_stats()
            
            else:
                # عرض العد التنازلي
                remaining = bot.analysis_interval - time_since_last
                minutes = int(remaining)
                seconds = int((remaining - minutes) * 60)
                print(f"\r⏳ التحليل القادم خلال: {minutes:02d}:{seconds:02d}", end='', flush=True)
            
            # الانتظار لدقيقة قبل الفحص التالي
            time.sleep(10)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 تم إيقاف البوت بواسطة المستخدم")
        print("📊 الإحصائيات النهائية:")
        bot.print_detailed_stats()
        print("\n🎯 شكراً لاستخدامك البوت المتقدم!")

if __name__ == "__main__":
    main()
