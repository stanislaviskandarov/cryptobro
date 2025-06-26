from .indicator_base import IndicatorBase

class MACDIndicator(IndicatorBase):
    def __init__(self, short_period=12, long_period=26, signal_period=9):
        self.short_period = short_period
        self.long_period = long_period
        self.signal_period = signal_period
        self.prices = []
        self.macd_line = []
        self.signal_line = []
        self.last_trend = "sideways"

    def ema(self, period, prices):
        k = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    def update(self, price: float):
        self.prices.append(price)
        if len(self.prices) > self.long_period:
            ema_short = self.ema(self.short_period, self.prices[-self.short_period:])
            ema_long = self.ema(self.long_period, self.prices[-self.long_period:])
            macd_value = ema_short - ema_long
            self.macd_line.append(macd_value)

            if len(self.macd_line) >= self.signal_period:
                signal = self.ema(self.signal_period, self.macd_line[-self.signal_period:])
                self.signal_line.append(signal)

                if macd_value > signal:
                    self.last_trend = "up"
                elif macd_value < signal:
                    self.last_trend = "down"
                else:
                    self.last_trend = "sideways"

    def get_trend(self) -> str:
        return self.last_trend
