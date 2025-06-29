import asyncio
import ccxt.pro
import aiohttp

from .trade_engine.trade_engine import TradeEngine

MIN_USDT_VOLUME = 1000000  # Минимальный объём торгов в USDT за 24ч
BANNED_PAIRS = {"TUSD/USDT", "BUSD/USDT", "USDC/USDT"}  # Чёрный список пар
MIN_PAIR_COUNT = 1  # Минимальное количество пар для обработки


class BinanceBatchTradeStream:
    def __init__(self, limit=10000, batch_size=50, delay_between_batches=5):
        self.exchange = ccxt.pro.binance()
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.limit = limit
        self.running = False
        self.apps = {}

    async def fetch_usdt_symbols(self):
        markets = await self.exchange.load_markets()
        tickers = await self.exchange.fetch_tickers()

        symbols = []
        for symbol, market in markets.items():
            if not symbol.endswith('/USDT') or not market['active']:
                continue
            if symbol in BANNED_PAIRS:
                continue

            ticker = tickers.get(symbol)
            if not ticker:
                continue

            volume = ticker.get('quoteVolume', 0)
            if volume and volume >= MIN_USDT_VOLUME:
                symbols.append(symbol)

        if MIN_PAIR_COUNT > 0:
            symbols = symbols[:MIN_PAIR_COUNT]
        print(f"Found {len(symbols)} liquid USDT pairs (min vol: {MIN_USDT_VOLUME})")
        return symbols

    async def stream_symbol(self, symbol):
        config = {
            'enabled_strategies': ['GigaStrategy'],
            'pair_name': symbol,
            'stock_name': "binance",
            'limit': 10000, # Количество хранимых трейдов
        }
        engine = TradeEngine(config)

        print(f"Subscribing to {symbol}")
        while self.running:
            # try:
                trade = await self.exchange.watch_trades(symbol)
                if isinstance(trade, list):
                    trade = trade[-1]
                await engine.add(trade)
            # except Exception as e:
            #     print(f"[{symbol}] WebSocket error: {e}")
            #     await asyncio.sleep(3)

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
