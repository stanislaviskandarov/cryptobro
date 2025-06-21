from sklearn.linear_model import LinearRegression
import numpy as np
from itertools import islice

from ..telega import send_telegram_message


class MyStrategy:
    def __init__(self, engine):
        self.engine = engine
        self.trades = engine.trades
        self.indicators = None

        self.calculator = IndicatorsCalculator()
        self.trend_detector = TrendDetector()
        self.evaluator = SignalEvaluator()

    async def process_trade(self):
        indicators = self.calculator.update(self.trades)
        trend = self.trend_detector.detect(self.trades)
        signal = self.evaluator.evaluate(indicators, trend)

        if signal:
            await self.send_signal(signal, indicators, trend)

    async def send_signal(self, direction, indicators, trend):
        from datetime import datetime

        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        symbol = self.engine.pair_name
        message = (
            "📊 *SIGNAL DETECTED*\n"
            f"{direction} after breakout\n"
            f"*Time:* `{now}`\n"
            f"*Pair:* `{symbol}`\n"
            f"*Price:* `{indicators['price']:,.5f}`\n"
            f"📈 *ΔSMA:* `{indicators['delta_sma']:.2f}%` *(was {self.evaluator.max_delta_sma:.2f}%)\n"
            f"📉 *ΔEMA:* `{indicators['delta_ema']:.2f}%` *(was {self.evaluator.max_delta_ema:.2f}%)\n"
            f"*Trend:* `{trend}`\n"
            f"💰 *Expected Profit:* `{self.evaluator.estimated_profit:.2f}%`"
        )
        await send_telegram_message(message, binance_symbol=symbol)
        print(message)


class IndicatorsCalculator:
    def __init__(self, ema_fast_alpha=0.3, ema_slow_alpha=0.05):
        self.ema_fast = None
        self.ema_slow = None
        self.avg_price_sum = 0.0
        self.ema_fast_alpha = ema_fast_alpha
        self.ema_slow_alpha = ema_slow_alpha

    def update(self, trades):
        if not trades:
            return None

        price = trades[-1]['price']
        if self.ema_fast is None:
            self.ema_fast = price
            self.ema_slow = price
        else:
            self.ema_fast = self.ema_fast_alpha * price + (1 - self.ema_fast_alpha) * self.ema_fast
            self.ema_slow = self.ema_slow_alpha * price + (1 - self.ema_slow_alpha) * self.ema_slow

        avg_price = sum(t['price'] for t in trades) / len(trades)
        delta_sma = ((price - avg_price) / avg_price) * 100
        delta_ema = ((price - self.ema_fast) / self.ema_fast) * 100

        return {
            'price': price,
            'avg_price': avg_price,
            'ema_fast': self.ema_fast,
            'ema_slow': self.ema_slow,
            'delta_sma': delta_sma,
            'delta_ema': delta_ema
        }


class TrendDetector:
    def __init__(self, window=50):
        self.window = window

    def detect(self, trades):
        if len(trades) < self.window:
            return "unknown"

        # Срез из deque с конца — через islice
        start = len(trades) - self.window
        last_trades = list(islice(trades, start, None))

        prices = np.array([t['price'] for t in last_trades])
        x = np.arange(len(prices)).reshape(-1, 1)
        y = prices.reshape(-1, 1)
        model = LinearRegression().fit(x, y)
        slope = model.coef_[0][0]

        if abs(slope) < 1e-4:
            return "sideways"
        return "up" if slope > 0 else "down"


class SignalEvaluator:
    def __init__(self, min_profit_threshold=0.2, fee_percent=0.1, slippage_ticks=2):
        self.active_signal = None
        self.max_delta_sma = 0.0
        self.max_delta_ema = 0.0
        self.min_profit_threshold = min_profit_threshold
        self.fee_percent = fee_percent
        self.slippage_ticks = slippage_ticks
        self.estimated_profit = 0.0

    def _estimated_profit(self, delta):
        return delta - (self.fee_percent * 2) - (self.slippage_ticks * 0.01)

    def evaluate(self, indicators, trend):
        delta_sma = indicators['delta_sma']
        delta_ema = indicators['delta_ema']

        if delta_sma > 0 and delta_ema > 0:
            profit = self._estimated_profit(min(delta_sma, delta_ema))
            if profit > self.min_profit_threshold:
                if self.active_signal != "up":
                    self.active_signal = "up"
                    self.max_delta_sma = delta_sma
                    self.max_delta_ema = delta_ema
                    self.estimated_profit = profit

        elif delta_sma < 0 and delta_ema < 0:
            profit = self._estimated_profit(-max(delta_sma, delta_ema))
            if profit > self.min_profit_threshold:
                if self.active_signal != "down":
                    self.active_signal = "down"
                    self.max_delta_sma = delta_sma
                    self.max_delta_ema = delta_ema
                    self.estimated_profit = profit

        reversal = None
        if self.active_signal == "up" and delta_sma < 0:
            reversal = "⬇️ REVERSAL DOWN"
            self.active_signal = None
        elif self.active_signal == "down" and delta_sma > 0:
            reversal = "⬆️ REVERSAL UP"
            self.active_signal = None

        return reversal