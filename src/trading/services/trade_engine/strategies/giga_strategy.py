from collections import deque
from datetime import datetime, timedelta

from ..valuer import Valuer


class TradePerIntervalAggregator:
    def __init__(self, interval = timedelta(seconds=2)):
        self.interval = interval
        self.current_time: datetime | None = None
        self.current_group: list[Valuer] = []

    def truncate_to_interval(self, dt: datetime) -> datetime:
        total_seconds = (dt - datetime.min).total_seconds()
        interval_seconds = self.interval.total_seconds()
        bucket = int(total_seconds // interval_seconds)
        return datetime.min + timedelta(seconds=bucket * interval_seconds)

    def process_trade(self, trade: Valuer) -> list[dict]:
        trade_time = self.truncate_to_interval(trade.t)
        result = []

        if self.current_time is None:
            self.current_time = trade_time

        if trade_time == self.current_time:
            self.current_group.append(trade)
            return []

        # 1. Вернуть текущую группу
        result.append({
            "start_time": self.current_time,
            "trades": self.current_group.copy()
        })

        # 2. Добавить пустые интервалы
        gap = int((trade_time - self.current_time).total_seconds() // self.interval.total_seconds())
        for i in range(1, gap):
            result.append({
                "start_time": self.current_time + i * self.interval,
                "trades": []
            })

        # 3. Начать новую группу
        self.current_time = trade_time
        self.current_group = [trade]

        return result


DIFF_LIMIT = 8
DIFFS_COUNT = 11

class GigaStrategy:
    def __init__(self, engine):
        self.engine = engine
        self.pair_name = engine.pair_name
        self.trades = engine.trades

        self.aggregator = TradePerIntervalAggregator()

        self.counter = 1
        self.diffs = [deque(maxlen=DIFF_LIMIT * (2 ** i)) for i in range(DIFFS_COUNT)]

    async def process_trade(self):
        if len(self.diffs[DIFFS_COUNT - 1]) % 8 == 0:
            await self.generate_report()

        self.counter += 1
        trade = self.trades[-1]

        trade_groups = self.aggregator.process_trade(trade)
        if len(trade_groups) > 0:
            for group in trade_groups:
                valuer = Valuer(datetime.now(), self.alfa_diff(group['trades']))
                self.diffs[DIFFS_COUNT - 1].append(valuer)

                for i in reversed(range(DIFFS_COUNT)):
                    if len(self.diffs[i]) % 2 == 0:
                        diff_avg = (self.diffs[i][-1].v + self.diffs[i][-2].v)/2.0
                        self.diffs[i - 1].append(
                            Valuer(datetime.fromtimestamp(self.diffs[i][-1].t.timestamp() + self.diffs[i][-2].t.timestamp() / 2), diff_avg)
                        )
                    else:
                        break
                    # self.print_diffs()

    def alfa_diff(self, trades):
        if len(trades) < 2:
            return 0.0

        diffs = [trades[i + 1].v - trades[i].v for i in range(len(trades) - 1)]

        pos_sum = sum(d for d in diffs if d > 0)
        neg_sum = sum(d for d in diffs if d < 0)

        return pos_sum + neg_sum

    # def print_diffs(self):
    #     print("================================================")
    #     print(self.pair_name)
    #     for i in reversed(range(DIFFS_COUNT)):
    #         print(f'{i:2} - {len(self.diffs[i]):10} - {self.diffs[i].maxlen}')
    #     print("================================================")

    async def generate_report(self):
        img_paths = []
        for i in reversed(range(DIFFS_COUNT)):
            img_path = f"{self.engine.stock_name}_{self.pair_name}_{i}.png"
            img_paths.append(img_path)
            await self.engine.chart_reporter.draw_valuer_stripe(self.diffs[i], img_path)
        await self.engine.chart_reporter.concatenate_images_vertically(img_paths, "lalalalla.png")
