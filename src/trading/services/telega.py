from telegram import Bot

TELEGRAM_BOT_TOKEN = "5045108885:AAFiFgJb4YyEsllnOP5grmqWpDYb1ExHzoE"
TELEGRAM_CHAT_ID = "@binansenoficarions"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_telegram_message(message: str, binance_symbol: str = None):
    if binance_symbol:
        message += f"\n[🔗 Перейти на Binance](https://www.binance.com/en/trade/{binance_symbol.replace('/', '_')})"

    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения в Telegram: {e}")
