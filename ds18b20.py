#!/usr/bin/python3
# -*- coding: utf-8 -*-
import datetime
import time
import RPi.GPIO as GPIO


SENSORS = {
    'outside': '/sys/bus/w1/devices/28-041661c3b1ff/w1_slave',
    'inside': '/sys/bus/w1/devices/28-031661b1c7ff/w1_slave',
}

GPIO.setmode(GPIO.BCM)


def print_temperatures(sensors):
    print('{}'.format(datetime.datetime.now().isoformat()))
    for name, sensor_path in sensors.items():
        with open(sensor_path, 'r') as sensor_fh:
            data = sensor_fh.readlines()

        if len(data) != 2:
            print('Unexpected data read from sensor '
                  '{name}:{data}'.format(**locals()))
            continue

        for line in data:
            if line.startswith('t='):
                break

        raw_temperature = int(line.split('=')[1])
        temperature = raw_temperature / 1000
        print('Sensor {name}: {temperature}°C'.format(**locals()))


try:
    while True:
        print_temperatures(SENSORS)
        print()
        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Program Exited Cleanly")
