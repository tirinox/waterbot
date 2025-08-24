from datetime import datetime
from io import BytesIO

import matplotlib.dates as mdates
from collections import deque
from matplotlib import pyplot as plt


def plot_water_level_chart(sensor_data: deque) -> BytesIO:
    times = []
    for entry in sensor_data:
        ts = entry["timestamp"]
        if isinstance(ts, (int, float)):
            # считаем, что ts — это количество секунд с эпохи
            times.append(datetime.fromtimestamp(ts))
        else:
            times.append(ts)

    levels = [entry["water_level"] for entry in sensor_data]

    if not times:
        raise ValueError("Нет данных для построения графика")
    # Рисуем график через фигуру/оси, чтобы контролировать форматирование дат
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(times, levels, marker='o', linestyle='-')

    # Настраиваем форматтер и локатор для дат на оси X
    locator = mdates.AutoDateLocator()  # автоматически выберет шаг (часы, дни и т.д.)
    formatter = mdates.DateFormatter('%d.%m %H:%M')  # формат: день.месяц часы:минуты
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # Подписи и заголовок
    ax.set_xlabel("Время")
    ax.set_ylabel("Уровень воды")
    ax.set_title("Уровень воды во времени")

    # Поворачиваем и подправляем отступы
    fig.autofmt_xdate()
    plt.tight_layout()

    # Save to BytesIO buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    plt.close()

    return buffer
