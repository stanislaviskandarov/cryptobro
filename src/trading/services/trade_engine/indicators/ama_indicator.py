from .indicator_base import IndicatorBase

class AMAIndicator(IndicatorBase):
    def __init__(self, period=10, fast=2, slow=30):
        self.period = period
        self.fast = 2 / (fast + 1)
        self.slow = 2 / (slow + 1)
        self.prices = []
        self.current_ama = None
        self.last_trend = "sideways"

    def update(self, price: float):
        self.prices.append(price)
        if len(self.prices) > self.period:
            change = abs(self.prices[-1] - self.prices[-self.period])
            volatility = sum(abs(self.prices[i] - self.prices[i-1]) for i in range(-self.period+1, 0))
            er = change / volatility if volatility != 0 else 0
            sc = (er * (self.fast - self.slow) + self.slow) ** 2

            if self.current_ama is None:
                self.current_ama = self.prices[-1]
            else:
                self.current_ama = self.current_ama + sc * (price - self.current_ama)

            delta = price - self.current_ama
            self.last_trend = "up" if delta > 0.1 else "down" if delta < -0.1 else "sideways"

    def get_trend(self) -> str:
        return self.last_trend
