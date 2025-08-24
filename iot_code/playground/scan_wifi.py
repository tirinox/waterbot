import time

import network

# Map authmode integers to human-readable strings
_AUTH_MODES = {
    0: 'OPEN',
    1: 'WEP',
    2: 'WPA-PSK',
    3: 'WPA2-PSK',
    4: 'WPA/WPA2-PSK',
    5: 'WPA2-ENTERPRISE'
}


def scan_and_print(wlan):
    nets = wlan.scan()
    print("{:<32} {:>6} {:>7} {:>12}".format("SSID", "RSSI", "CHAN", "SECURITY"))
    print("-" * 60)
    for ssid, bssid, channel, rssi, authmode, hidden in nets:
        ssid = ssid.decode('utf-8', 'ignore') if isinstance(ssid, bytes) else str(ssid)
        sec = _AUTH_MODES.get(authmode, str(authmode))
        print("{:<32} {:>6} {:>7} {:>12}".format(ssid, rssi, channel, sec))
    print()


def scan_main():
    wlan = network.WLAN(network.STA_IF)

    while True:
        try:
            wlan.active(False)
            time.sleep(0.1)
            wlan.active(True)

            print("Scanning for Wi-Fi networks…")
            scan_and_print(wlan)

        except OSError as e:
            print("Scan error:", e)

        time.sleep(5)
