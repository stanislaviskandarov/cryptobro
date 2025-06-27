from collections import deque

from ..indicators.ama_indicator import AMAIndicator
from ..indicators.macd_indicator import MACDIndicator
from ..indicators.supertrend_indicator import SuperTrendIndicator


class GigaStrategy:
    def __init__(self, engine):
        self.engine = engine
        self.pair_name = engine.pair_name

        self.trades = engine.trades
        self.alpha_diff = deque(maxlen=engine.config['limit'])
        self.beta_diff = deque(maxlen=engine.config['limit'])

        self.indicators = [
            MACDIndicator(),
            AMAIndicator(),
            SuperTrendIndicator()
        ]
        self.counter = 1

    async def process_trade(self):
        if self.counter % 500 == 0:
            self.generate_report()
        self.counter += 1
        trade = self.trades[-1]
        for indicator in self.indicators:
            indicator.update(trade.get('price'))

        if len(self.trades) > 2:
            diff = self.trades[-1]['price'] - self.trades[-3]['price']
            self.alpha_diff.append({"datetime": trade.get("datetime"), "price": diff})

        if len(self.alpha_diff) > 2:
            diff2 = self.alpha_diff[-1]['price'] - self.alpha_diff[-3]['price']
            self.beta_diff.append({"datetime": trade.get("datetime"), "price": diff2})

    def get_combined_trend(self) -> str:
        trends = [ind.get_trend() for ind in self.indicators]
        up_count = trends.count('up')
        down_count = trends.count('down')
        sideways_count = trends.count('sideways')

        if up_count > down_count and up_count > sideways_count:
            return 'up'
        elif down_count > up_count and down_count > sideways_count:
            return 'down'
        else:
            return 'sideways'

    def generate_report(self):
        self.engine.chart_reporter.generate_and_send(
            list(self.trades),
            list(self.alpha_diff),
            list(self.beta_diff)
        )
