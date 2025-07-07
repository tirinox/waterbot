import time

import machine
import neopixel

from private_const import PIN, DELAY
from utils import hue_to_rgb

# Configure 1 WS2812 LED on pin 16
pin = machine.Pin(PIN)
np = neopixel.NeoPixel(pin, 1)  # '1' means a single LED


def main():
    hue = 0
    while True:
        # np[0] = (5, 0, 0)  # Red
        # np.write()
        # time.sleep(0.5)

        np[0] = hue_to_rgb(hue)
        np.write()
        time.sleep(DELAY)

        hue += 1
        if hue >= 360:
            hue = 0  # Reset hue after a full cycle


if __name__ == "__main__":
    main()
