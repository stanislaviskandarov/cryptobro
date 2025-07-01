from datetime import datetime
import matplotlib.pyplot as plt
import os
from PIL import Image
import numpy as np
import asyncio
from django.conf import settings

from .telega import send_telegram_image, send_telegram_message


class ChartReporter:
    def __init__(self, pair_name):
        self.pair_name = pair_name
        self.tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.safe_pair_name = self.pair_name.replace("/", "_")

    async def draw_valuer_stripe(self, valuers: list, path: str, width: int = 6000, height: int = 64, k: float = 0.001):
        full_width = width + 100  # +100px отступ слева
        save_path = os.path.join(self.tmp_dir, path)

        n = len(valuers)
        pixels = np.full((height, full_width, 3), fill_value=255, dtype=np.uint8)

        for idx, val in enumerate(valuers):
            x_start = int(idx * width / n) + 100
            x_end = int((idx + 1) * width / n) + 100
            color = (128, 128, 128)  # gray

            if val.v > k:
                color = (0, 255, 0)  # green
            elif val.v < -k:
                color = (255, 0, 0)  # red

            for x in range(x_start, min(x_end, full_width)):
                pixels[:, x] = color

        plt.figure(figsize=(full_width / 100, height / 100), dpi=100)
        plt.imshow(pixels, aspect='auto')
        plt.axis('off')
        plt.savefig(save_path, bbox_inches='tight', pad_inches=0)
        plt.close()

    def generate_and_send(self, trades, alfa_diff, beta_diff):
        path1 = os.path.join(self.tmp_dir, f"{self.safe_pair_name}_trades.png")
        path2 = os.path.join(self.tmp_dir, f"{self.safe_pair_name}_alfa.png")
        path3 = os.path.join(self.tmp_dir, f"{self.safe_pair_name}_beta.png")
        final_path = os.path.join(self.tmp_dir, f"{self.safe_pair_name}.png")

        self.plot_and_save_array(trades, "Trades", path1, mode="line")
        self.plot_and_save_array(alfa_diff, "Alfa Diff", path2, mode="dots")
        self.plot_and_save_array(beta_diff, "Beta Diff", path3, mode="dots")

        result = self.concatenate_images_vertically([path1, path2, path3], final_path)

        caption = f"{self.safe_pair_name} — графики: цена, альфа, бета"
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

    def plot_and_save_array(self, data, label, save_path, mode="line"):
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

    async def concatenate_images_vertically(self, image_names, save_name):
        save_path = os.path.join(self.tmp_dir, save_name)
        images = [Image.open(os.path.join(self.tmp_dir, name)) for name in image_names]
        if not images:
            return None

        widths, heights = zip(*(img.size for img in images))
        total_height = sum(heights)
        max_width = max(widths)

        result = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))

        y_offset = 0
        for img in images:
            x_offset = (max_width - img.width) // 2  # центрируем по ширине
            result.paste(img, (x_offset, y_offset))
            y_offset += img.height

        result.save(save_path)
        return save_path