from django.core.management.base import BaseCommand
import asyncio
from trading.services.binance_stream import BinanceBatchTradeStream


class Command(BaseCommand):
    help = "Запустить Binance WebSocket стрим"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Запуск BinanceBatchTradeStream...")
        try:
            asyncio.run(self.run_stream())
        except Exception as e:
            self.stderr.write(f"❌ Ошибка: {e}")

    async def run_stream(self):
        stream = BinanceBatchTradeStream()
        try:
            await stream.run()
        except KeyboardInterrupt:
            print("⏹ Остановка по Ctrl+C")
            await stream.stop()
        except Exception as e:
            print(f"❗️ Runtime error: {e}")
            await stream.stop()
        finally:
            print("🔚 Работа завершена")