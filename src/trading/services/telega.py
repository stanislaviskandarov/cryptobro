# from telegram import Bot
import requests

TELEGRAM_CHAT_ID = "@binansenoficarions"
TELEGRAM_BOT_TOKEN = "5045108885:AAFiFgJb4YyEsllnOP5grmqWpDYb1ExHzoE"


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"[Telegram] Ошибка при отправке текста: {e}")


def send_telegram_image(caption: str, file_path: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(file_path, "rb") as f:
            files = {"photo": f}
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption
            }
            requests.post(url, data=data, files=files, timeout=10)
    except Exception as e:
        print(f"[Telegram] Ошибка при отправке изображения: {e}")

