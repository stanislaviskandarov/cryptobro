import asyncio
import ccxt.pro
from collections import deque
from datetime import datetime
import aiohttp

TELEGRAM_BOT_TOKEN = "5045108885:AAFiFgJb4YyEsllnOP5grmqWpDYb1ExHzoE"
TELEGRAM_CHAT_ID = "@binansenoficarions"


async def send_telegram_message(message, binance_symbol=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    keyboard = {
        "inline_keyboard": [[
            {
                "text": "🔗 Перейти на Binance",
                "url": f"https://www.binance.com/en/trade/{binance_symbol.replace('/', '_')}"
            }
        ]]
    } if binance_symbol else None

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if keyboard:
        data["reply_markup"] = keyboard

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as resp:
            if resp.status != 200:
                print(f"⚠️ Telegram error: {await resp.text()}")


class PairBuffer:
    def __init__(self, pair_name, stock_name, life_time=20, buffer_limit=1000):
        self.pair_name = pair_name
        self.stock_name = stock_name
        self.life_time = life_time
        self.buffer_limit = buffer_limit
        self.trades = deque(maxlen=self.buffer_limit)

    def __getitem__(self, index):
        return self.trades[index]

    def size(self):
        return len(self.trades)

    def add(self, trade):
        self.trades.append(trade)


class IndicatorsCalculator:
    def __init__(self, buffer: PairBuffer, ema_fast_alpha=0.3, ema_slow_alpha=0.05):
        self.buffer = buffer
        self._avg_price_sum = 0.0
        self.avg = 0.0
        self.ema_fast = None
        self.ema_slow = None
        self.ema_fast_alpha = ema_fast_alpha
        self.ema_slow_alpha = ema_slow_alpha
        self.trend = "unknown"
        self.prev_price = None
        self.delta_sma = 0.0
        self.delta_ema = 0.0

    def update(self, trade):
        price = trade['price']

        if len(self.buffer.trades) == self.buffer.buffer_limit:
            removed = self.buffer.trades[0]
            self._avg_price_sum -= removed['price']
        self._avg_price_sum += price
        self.avg = self._avg_price_sum / len(self.buffer.trades)

        if self.ema_fast is None:
            self.ema_fast = price
        else:
            self.ema_fast = self.ema_fast_alpha * price + (1 - self.ema_fast_alpha) * self.ema_fast

        if self.ema_slow is None:
            self.ema_slow = price
        else:
            self.ema_slow = self.ema_slow_alpha * price + (1 - self.ema_slow_alpha) * self.ema_slow

        if abs(self.ema_fast - self.ema_slow) / self.ema_slow < 0.002:
            self.trend = "sideways"
        elif self.ema_fast > self.ema_slow:
            self.trend = "up"
        else:
            self.trend = "down"

        if self.prev_price:
            self.delta_sma = ((price - self.avg) / self.avg) * 100
            self.delta_ema = ((price - self.ema_fast) / self.ema_fast) * 100

        self.prev_price = price

    def __str__(self):
        return (
            f"[{len(self.buffer.trades):>4}] "
            f"avg={self.avg:>12.2f} "
            f"trend={self.trend:<9} "
            f"{self.buffer.stock_name:<10} "
            f"{self.buffer.pair_name:<12}"
        )


class SignalEvaluator:
    def __init__(self, calculator: IndicatorsCalculator, threshold=0.5):
        self.calculator = calculator
        self.threshold = threshold
        self.active_signal = None
        self.max_delta_sma = 0.0
        self.max_delta_ema = 0.0

    def evaluate(self, trade):
        price = trade['price']
        symbol = self.calculator.buffer.pair_name
        trend = self.calculator.trend
        delta_sma = self.calculator.delta_sma
        delta_ema = self.calculator.delta_ema

        if delta_sma > self.threshold and delta_ema > self.threshold:
            if self.active_signal != "up":
                self.active_signal = "up"
                self.max_delta_sma = delta_sma
                self.max_delta_ema = delta_ema

        elif delta_sma < -self.threshold and delta_ema < -self.threshold:
            if self.active_signal != "down":
                self.active_signal = "down"
                self.max_delta_sma = delta_sma
                self.max_delta_ema = delta_ema

        if self.active_signal == "up" and delta_sma < 0:
            asyncio.create_task(self._send_signal("⬇️ REVERSAL DOWN", symbol, price, delta_sma, delta_ema, trend))
            self.active_signal = None

        elif self.active_signal == "down" and delta_sma > 0:
            asyncio.create_task(self._send_signal("⬆️ REVERSAL UP", symbol, price, delta_sma, delta_ema, trend))
            self.active_signal = None

    async def _send_signal(self, direction, symbol, price, delta_sma, delta_ema, trend):
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        message = (
            "📊 *SIGNAL DETECTED*\n"
            f"{direction} after breakout\n"
            f"*Time:* `{now}`\n"
            f"*Pair:* `{symbol}`\n"
            f"*Price:* `{price:,.5f}`\n"
            f"📈 *ΔSMA:* `{delta_sma:.2f}%` *(was {self.max_delta_sma:.2f}%)\n"
            f"📉 *ΔEMA:* `{delta_ema:.2f}%` *(was {self.max_delta_ema:.2f}%)\n"
            f"*Trend:* `{trend}`"
        )
        await send_telegram_message(message, binance_symbol=symbol)
        print(message)


class PairBuffers:
    def __init__(self):
        self.pair_buffers = []

    def add(self, pair_buffer):
        self.pair_buffers.append(pair_buffer)

    def buffer_by(self, pair_name, stock_name):
        for pair in self.pair_buffers:
            if pair.pair_name == pair_name and pair.stock_name == stock_name:
                return pair
        return None

    def all(self):
        return self.pair_buffers


class BinanceBatchTradeStream:
    def __init__(self, maxlen=1000, batch_size=50, delay_between_batches=5):
        self.exchange = ccxt.pro.binance()
        self.buffers = PairBuffers()
        self.calculators = {}
        self.evaluators = {}
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.buffer_limit = maxlen
        self.running = False

    async def fetch_usdt_symbols(self):
        markets = await self.exchange.load_markets()
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s]['active']]
        print(f"Found {len(symbols)} USDT pairs")
        return symbols

    async def stream_symbol(self, symbol):
        pair_buffer = PairBuffer(pair_name=symbol, stock_name="binance", buffer_limit=self.buffer_limit)
        calculator = IndicatorsCalculator(pair_buffer)
        evaluator = SignalEvaluator(calculator)
        self.buffers.add(pair_buffer)
        self.calculators[symbol] = calculator
        self.evaluators[symbol] = evaluator

        print(f"Subscribing to {symbol}")
        while self.running:
            try:
                trade = await self.exchange.watch_trades(symbol)
                if isinstance(trade, list):
                    trade = trade[-1]
                pair_buffer.add(trade)
                calculator.update(trade)
                evaluator.evaluate(trade)
                # print(f"{calculator} --- {trade['price']} x {trade['amount']}")
            except Exception as e:
                print(f"[{symbol}] WebSocket error: {e}")
                await asyncio.sleep(3)

    async def run(self):
        self.running = True
        try:
            symbols = await self.fetch_usdt_symbols()
            batches = [symbols[i:i + self.batch_size] for i in range(0, len(symbols), self.batch_size)]

            for i, batch in enumerate(batches):
                print(f"▶️ Starting batch {i + 1}/{len(batches)}: {len(batch)} symbols")

                for symbol in batch:
                    asyncio.create_task(self.stream_symbol(symbol))

                await asyncio.sleep(self.delay_between_batches)

            while self.running:
                await asyncio.sleep(10)

        except Exception as e:
            print(f"🚨 Error in run(): {e}")

        finally:
            print("🛑 Closing Binance connection")
            await self.exchange.close()

    async def stop(self):
        self.running = False
        print("🔻 Stopping stream...")
        await self.exchange.close()
        print("✅ Connection closed")

    def get_buffers(self):
        return self.buffers.all()
