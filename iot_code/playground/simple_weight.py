import time

from lib.const import SCALE_FACTOR
from lib.scale import get_new_scale, get_weight_kg


def run_weight():
    hx711 = get_new_scale()

    print("Taring scale…")
    hx711.tare()
    print("Ready. Beginning readings.\n")

    # === Read loop ===
    while True:
        try:
            # get a single reading (in your calibrated units)
            weight = hx711.get_value()
            kg = get_weight_kg(hx711)
            print(f"{kg} kg = {weight} units")
        except Exception as e:
            print("Read error:", e)
        time.sleep(0.1)

