import time

import machine
import network
import random
import ujson
import urequests

from const import LED_PIN
from private_const import WIFI_SSID, WIFI_PASSWORD, CALLBACK_HOST, SHARED_SECRET, PIN
from utils import led_blink

# === Pin setup ===
water_pin = machine.Pin(LED_PIN, machine.Pin.IN)


# === Wi-Fi connection ===
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            # fast blink: 10 quick on/off cycles (~1 s total)
            led_blink(times=10, delay_on=0.05)
    print('Connected, IP address:', wlan.ifconfig()[0])


# === Water level reading (stub) ===
def get_water_level():
    # TODO: replace with actual sensor reading (e.g. ADC)
    return random.randint(1, 100)


# === POST data ===
def send_data(level):
    try:
        # one quick blink before request
        led_blink(times=1, delay_on=0.1)

        payload = ujson.dumps({
            'water_level': level,
            'secret': SHARED_SECRET
        })
        headers = {'Content-Type': 'application/json'}
        response = urequests.post(CALLBACK_HOST, data=payload, headers=headers)
        print('Sent:', payload, 'Status:', response.status_code)
        response.close()

        # two slow blinks after success
        led_blink(times=2, delay_on=0.2)

    except Exception as e:
        print('Error sending data:', e)


# === Main loop ===
def sensor_main():
    connect_wifi()
    while True:
        lvl = get_water_level()
        send_data(lvl)
        time.sleep(5)
