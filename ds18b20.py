#!/usr/bin/python3
# -*- coding: utf-8 -*-
import datetime
import graphitesend
import statsd
import time
import RPi.GPIO as GPIO

from graphitesend import GraphiteSendException

SENSORS = {
    'outside': '/sys/bus/w1/devices/28-041661c3b1ff/w1_slave',
    'inside': '/sys/bus/w1/devices/28-031661b1c7ff/w1_slave',
}
FILE_OUT = 'temperature.csv'

try:
    graphitesend.init(graphite_server='localhost')
    GRAPHITE_OUT = True
except GraphiteSendException:
    GRAPHITE_OUT = False
    print('Could not find Carbon. Not sending data to graphite.')


GPIO.setmode(GPIO.BCM)


def print_temperatures(sensors):
    now = datetime.datetime.now().isoformat()
    print('{}'.format(now))
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

        if GRAPHITE_OUT:
            graphitesend.send('temp_' + name, temperature)

        if FILE_OUT:
            with open(FILE_OUT, 'a') as out_fh:
                out_fh.write('{now},{name}={temperature}\n'.format(**locals()))

        print('Sensor {name}: {temperature}°C'.format(**locals()))


try:
    while True:
        print_temperatures(SENSORS)
        print()
        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Program Exited Cleanly")
