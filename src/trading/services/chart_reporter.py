from datetime import datetime
import matplotlib.pyplot as plt
import os
from PIL import Image
from django.conf import settings

from .telega import send_telegram_image, send_telegram_message


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
