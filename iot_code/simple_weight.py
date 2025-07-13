import time

from machine import Pin

from const import HX711_DAT_PIN, HX711_CLK_PIN, SCALE_FACTOR
from drivers.hx711 import HX711


def get_new_scale():
    pin_out = Pin(HX711_DAT_PIN, Pin.IN, pull=Pin.PULL_DOWN)
    pin_sck = Pin(HX711_CLK_PIN, Pin.OUT)
    hx711 = HX711(pin_sck, pin_out)
    return hx711


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


def get_weight_kg(hx711):
    readings = hx711.get_value()
    return readings / SCALE_FACTOR
