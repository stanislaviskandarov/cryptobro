import asyncio
import ccxt.pro
import aiohttp

from .trade_engine.trade_engine import TradeEngine

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
        symbols = [s for s in markets if s.endswith('/USDT') and markets[s]['active']]
        print(f"Found {len(symbols)} USDT pairs")
        return symbols

    async def stream_symbol(self, symbol):
        config = {
            'enabled_strategies': ['GigaStrategy'],
            'limit': 10000, # Количество хранимых трейдов
        }
        engine = TradeEngine(pair_name=symbol, stock_name="binance", config=config)

        print(f"Subscribing to {symbol}")
        while self.running:
            try:
                trade = await self.exchange.watch_trades(symbol)
                if isinstance(trade, list):
                    trade = trade[-1]
                # print(trade)
                await engine.add(trade)
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