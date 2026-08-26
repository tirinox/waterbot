import time

import machine
import network
import ujson
import urequests

from lib.const import LED_PIN
from lib.led import led_blink
from playground.simple_weight import get_new_scale, get_weight_kg
from private_const import WIFI_SSID, WIFI_PASSWORD, CALLBACK_HOST, SHARED_SECRET, DELAY

# === Pin setup ===
water_pin = machine.Pin(LED_PIN, machine.Pin.IN)

hx711 = get_new_scale()


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


# === Water level reading ===
def get_water_level():
    weight = hx711.get_value()
    kg = get_weight_kg(hx711)
    print(f"Measured {kg} kg = {weight} units")
    return kg


# === POST data ===
def send_data(level, tare_completed=False):
    response = None
    try:
        # one quick blink before request
        led_blink(times=1, delay_on=0.1)

        data = {
            'water_level': level,
            'secret': SHARED_SECRET
        }
        if tare_completed:
            data['tare_completed'] = True

        payload = ujson.dumps(data)
        headers = {'Content-Type': 'application/json'}
        response = urequests.post(CALLBACK_HOST, data=payload, headers=headers)
        print('Sent Status:', response.status_code)
        status_code = response.status_code
        response_data = response.json()
        response.close()
        response = None

        if status_code != 200:
            return False, False

        # two slow blinks after success
        led_blink(times=2, delay_on=0.2)
        return True, response_data.get('tare', False) is True

    except Exception as e:
        print('Error sending data:', e)
        return False, False
    finally:
        if response is not None:
            response.close()


# === Main loop ===
def sensor_main():
    connect_wifi()

    print("Taring scale…")
    hx711.tare()
    print("Ready. Beginning readings.\n")

    tare_completed = False
    while True:
        lvl = get_water_level()
        sent, tare_requested = send_data(lvl, tare_completed)
        if sent:
            tare_completed = False
        if tare_requested:
            print("Tare requested by Telegram command…")
            hx711.tare()
            tare_completed = True
            print("Tare complete.")
        time.sleep(DELAY)
