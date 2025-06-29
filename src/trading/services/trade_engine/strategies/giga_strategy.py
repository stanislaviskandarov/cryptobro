from collections import deque
from datetime import datetime, timedelta

from ..indicators.ama_indicator import AMAIndicator
from ..indicators.macd_indicator import MACDIndicator
from ..indicators.supertrend_indicator import SuperTrendIndicator
from ..valuer import Valuer


INTERVAL = timedelta(seconds=2)

class TradePerIntervalAggregator:
    def __init__(self):
        self.current_time: datetime | None = None
        self.current_group: list[Valuer] = []

    def truncate_to_interval(self, dt: datetime) -> datetime:
        total_seconds = (dt - datetime.min).total_seconds()
        interval_seconds = INTERVAL.total_seconds()
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
        gap = int((trade_time - self.current_time).total_seconds() // INTERVAL.total_seconds())
        for i in range(1, gap):
            result.append({
                "start_time": self.current_time + i * INTERVAL,
                "trades": []
            })

        # 3. Начать новую группу
        self.current_time = trade_time
        self.current_group = [trade]

        return result



BASE_DIFF_LIMIT = 8
DIFF_DEQUE_COUNT = 11


class GigaStrategy:
    def __init__(self, engine):
        self.engine = engine
        self.pair_name = engine.pair_name

        self.trades = engine.trades
        self.aggregator = TradePerIntervalAggregator()

        self.diffs = [deque(maxlen=BASE_DIFF_LIMIT * (2 ** i)) for i in range(DIFF_DEQUE_COUNT)]

        self.indicators = [
            MACDIndicator(),
            AMAIndicator(),
            SuperTrendIndicator()
        ]
        self.counter = 1

    async def process_trade(self):
        if len(self.diffs[DIFF_DEQUE_COUNT - 1]) % 8 == 0:
            img_paths = []
            for i in reversed(range(DIFF_DEQUE_COUNT)):
                img_path = f"{i}.png"
                img_paths.append(img_path)
                self.engine.chart_reporter.draw_valuer_stripe(self.diffs[i], img_path)
            self.engine.chart_reporter.concatenate_images_vertically(img_paths, "lalalalla.png")
        self.counter += 1
        trade = self.trades[-1]
        for indicator in self.indicators:
            indicator.update(trade.v)

        trade_groups = self.aggregator.process_trade(trade)
        if len(trade_groups) > 0:
            for group in trade_groups:
                valuer = Valuer(datetime.now(), self.alfa_diff(group['trades']))
                self.diffs[DIFF_DEQUE_COUNT - 1].append(valuer)

                for i in reversed(range(DIFF_DEQUE_COUNT)):
                    if len(self.diffs[i]) % 2 == 0:
                        diff_avg = (self.diffs[i][-1].v + self.diffs[i][-2].v)/2.0
                        self.diffs[i - 1].append(
                            Valuer(datetime.fromtimestamp(self.diffs[i][-1].t.timestamp() + self.diffs[i][-2].t.timestamp() / 2), diff_avg)
                        )
                    else:
                        break
                    self.print_diffs()

    def alfa_diff(self, trades):
        if len(trades) < 2:
            return 0.0

        diffs = [trades[i + 1].v - trades[i].v for i in range(len(trades) - 1)]

        pos_sum = sum(d for d in diffs if d > 0)
        neg_sum = sum(d for d in diffs if d < 0)

        return pos_sum + neg_sum


    def print_diffs(self):
        print("================================================")
        print(self.pair_name)
        for i in reversed(range(DIFF_DEQUE_COUNT)):
            print(f'{i:2} - {len(self.diffs[i]):10} - {self.diffs[i].maxlen}')
        print("================================================")

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
