from collections import deque
import asyncio

# Ниже указанные зависимости нужны, даже если они отображаются как неиспользуемые
from .my_strategy import MyStrategy


class TradeEngine:
    def __init__(self, pair_name, stock_name, config = {}, limit=10000):
        self.pair_name = pair_name
        self.stock_name = stock_name
        self.trades = deque(maxlen=limit)
        self.strategies = None
        self.init_strategies(config)

    def init_basic_indicators(self):
        pass

    def init_strategies(self, config):
        self.strategies = [globals()[name](self) for name in config['enabled_strategies']]

    def add_strategy(self, strategy):
        self.strategies.append(strategy)

    def remove_strategy(self, strategy):
        self.strategies.remove(strategy)

    def list_strategy(self):
        return [strategy.name for strategy in self.strategies]

    async def add(self, trade):
        self.trades.append(trade)
        await self.on_update()

    async def on_update(self) -> None:
        await asyncio.gather(
            *[strategy.process_trade() for strategy in self.strategies]
        )
