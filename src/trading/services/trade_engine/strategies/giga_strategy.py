from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt
import os
import requests
from PIL import Image
from django.conf import settings


TELEGRAM_BOT_TOKEN = "5045108885:AAFiFgJb4YyEsllnOP5grmqWpDYb1ExHzoE"


class GigaStrategy:
    def __init__(self, engine):
        self.engine = engine
        self.trades = engine.trades
        self.alfa_diff = deque(maxlen=self.engine.config['limit'])
        self.beta_diff = deque(maxlen=self.engine.config['limit'])
        self.counter = 1
        self.reporter = ChartReporter(engine.pair_name)

    async def process_trade(self):
        self.next_alfa()
        self.next_beta()
        self.check_chart_trigger()
        self.counter += 1
        if self.counter >= self.engine.config['limit']:
            self.counter = 1

    def next_alfa(self):
        if len(self.trades) < 2:
            return
        self.alfa_diff.append({
            'price': self.trades[-1]['price'] - self.trades[-2]['price'],
            'datetime': datetime.now(),
        })

    def next_beta(self):
        if len(self.alfa_diff) < 2:
            return
        self.beta_diff.append({
            'price': self.alfa_diff[-1]['price'] - self.alfa_diff[-2]['price'],
            'datetime': datetime.now(),
        })

    def check_chart_trigger(self):
        if self.counter % 5000 == 0:
            self.reporter.generate_and_send(self.trades, self.alfa_diff, self.beta_diff)


class ChartReporter:
    def __init__(self, pair_name):
        self.pair_name = pair_name
        self.tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.safe_pair_name = self.pair_name.replace("/", "_")

    def generate_and_send(self, trades, alfa_diff, beta_diff):
        path1 = os.path.join(self.tmp_dir, f"{self.safe_pair_name}_trades.png")
        path2 = os.path.join(self.tmp_dir, f"{self.safe_pair_name}_alfa.png")
        path3 = os.path.join(self.tmp_dir, f"{self.safe_pair_name}_beta.png")
        final_path = os.path.join(self.tmp_dir, f"{self.safe_pair_name}.png")

        self.plot_and_save(trades, "Trades", path1, mode="line")
        self.plot_and_save(alfa_diff, "Alfa Diff", path2, mode="dots")
        self.plot_and_save(beta_diff, "Beta Diff", path3, mode="dots")

        result = self.concatenate_images_vertically([path1, path2, path3], final_path)

        caption = f"📊 {self.safe_pair_name} — графики: цена, альфа, бета"
        if result:
            send_telegram_image(caption, file_path=final_path)
        else:
            send_telegram_message(f"Ошибка генерации графиков для {self.safe_pair_name}")

    def extract_time_price(self, data):
        times = []
        prices = []
        for entry in data:
            try:
                if isinstance(entry.get("datetime"), datetime):
                    time = entry["datetime"]
                elif "datetime" in entry:
                    time = datetime.fromisoformat(entry["datetime"].replace("Z", "+00:00"))
                elif "timestamp" in entry:
                    time = datetime.utcfromtimestamp(entry["timestamp"] / 1000)
                else:
                    continue
                times.append(time)
                prices.append(entry["price"])
            except Exception as e:
                print(f"[extract_time_price] Пропущен элемент: {entry}, ошибка: {e}")
        return times, prices

    def plot_and_save(self, data, label, save_path, mode="line"):
        times, prices = self.extract_time_price(data)
        if not times or not prices:
            return

        max_price = max(prices)
        min_price = min(prices)
        y_min = min_price * 0.95
        y_max = max_price * 1.05

        plt.figure(figsize=(12, 4))
        if mode == "line":
            plt.plot(times, prices, label=label, linewidth=2)
        elif mode == "dots":
            plt.scatter(times, prices, label=label, s=10)
        else:
            raise ValueError(f"Неизвестный режим графика: {mode}")

        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.title(f'{label} — {self.pair_name}')
        plt.ylim(y_min, y_max)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()

    def concatenate_images_vertically(self, image_paths, save_path):
        images = [Image.open(p) for p in image_paths if os.path.exists(p)]
        if not images:
            return None

        widths, heights = zip(*(img.size for img in images))
        total_height = sum(heights)
        max_width = max(widths)

        result = Image.new('RGB', (max_width, total_height))

        y_offset = 0
        for img in images:
            result.paste(img, (0, y_offset))
            y_offset += img.height

        result.save(save_path)
        return save_path


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": "@binansenoficarions",
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
                "chat_id": "@binansenoficarions",
                "caption": caption
            }
            requests.post(url, data=data, files=files, timeout=10)
    except Exception as e:
        print(f"[Telegram] Ошибка при отправке изображения: {e}")
