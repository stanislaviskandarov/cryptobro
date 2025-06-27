from collections import deque
import asyncio

from .strategies.giga_strategy import GigaStrategy
from ..chart_reporter import ChartReporter

STRATEGIES = {
    'GigaStrategy': GigaStrategy,
}

class TradeEngine:
    def __init__(self, config):
        self.pair_name = config['pair_name']
        self.stock_name = config['stock_name']
        self.config = config
        self.trades = deque(maxlen=self.config['limit'])
        self.chart_reporter = ChartReporter(self.pair_name)

        self.strategies = None
        self.init_strategies(config)

    def init_strategies(self, config):
        self.strategies = [STRATEGIES[name](self) for name in config['enabled_strategies']]

    def add_strategy(self, strategy):
        self.strategies.append(strategy)

    def remove_strategy(self, strategy):
        self.strategies.remove(strategy)

    def list_strategy(self):
        return [strategy.name for strategy in self.strategies]

    # {'info': {'e': 'trade', 'E': 1750958244666, 's': 'BTCUSDT', 't': 5048890612, 'p': '107275.00000000',
    #           'q': '0.01770000', 'T': 1750958244666, 'm': True, 'M': True}, 'timestamp': 1750958244666,
    #  'datetime': '2025-06-26T17:17:24.666Z', 'symbol': 'BTC/USDT', 'id': '5048890612', 'order': None, 'type': None,
    #  'side': 'sell', 'takerOrMaker': None, 'price': 107275.0, 'amount': 0.0177, 'cost': 1898.7675,
    #  'fee': {'cost': None, 'currency': None}, 'fees': []}
    async def add(self, trade):
        self.trades.append(trade)
        await self.on_update()

    async def on_update(self) -> None:
        await asyncio.gather(
            *[strategy.process_trade() for strategy in self.strategies]
        )
