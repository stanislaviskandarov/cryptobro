from .indicator_base import IndicatorBase

class SuperTrendIndicator(IndicatorBase):
    def __init__(self, atr_period=7, multiplier=3):
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.prices = []
        self.prev_close = None
        self.trend = "sideways"

    def update(self, price: float):
        self.prices.append(price)
        if len(self.prices) < self.atr_period + 1:
            return

        trs = [abs(self.prices[i] - self.prices[i-1]) for i in range(-self.atr_period+1, 0)]
        atr = sum(trs) / self.atr_period
        hl2 = (price + self.prices[-2]) / 2
        upper_band = hl2 + self.multiplier * atr
        lower_band = hl2 - self.multiplier * atr

        if self.prev_close:
            if self.prev_close > upper_band:
                self.trend = "down"
            elif self.prev_close < lower_band:
                self.trend = "up"
            else:
                self.trend = self.trend or "sideways"

        self.prev_close = price

    def get_trend(self) -> str:
        return self.trend
