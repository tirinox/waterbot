from machine import Pin

from drivers.hx711 import HX711
from .const import HX711_DAT_PIN, HX711_CLK_PIN, SCALE_FACTOR


def get_new_scale():
    pin_out = Pin(HX711_DAT_PIN, Pin.IN, pull=Pin.PULL_DOWN)
    pin_sck = Pin(HX711_CLK_PIN, Pin.OUT)
    hx711 = HX711(pin_sck, pin_out)
    return hx711


def get_weight_kg(hx711):
    readings = hx711.get_value()
    return readings / SCALE_FACTOR
