import time

import machine

led = machine.Pin(8, machine.Pin.OUT)


# === LED utility (unified) ===
def led_blink(times=1, delay_on=0.2, delay_off=None):
    if delay_off is None:
        delay_off = delay_on
    for _ in range(times):
        led.on()
        time.sleep(delay_on)
        led.off()
        time.sleep(delay_off)
