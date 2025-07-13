from sensor_send import sensor_main
from simple_weight import run_weight
from utils import led_blink


def main():
    print("WaterBot welcome!")
    led_blink(5, 0.1, 0.2)
    sensor_main()
    # run_weight()


if __name__ == '__main__':
    main()
