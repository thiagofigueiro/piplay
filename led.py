#!/usr/bin/python3
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import signal
import sys
import time

# https://thepihut.com/blogs/raspberry-pi-tutorials/27968772-turning-on-an-led-with-your-raspberry-pis-gpio-pins
YELLOW_PIN = 23
GREEN_PIN = 24
RED_PIN = 25
ALL_PINS = (YELLOW_PIN, GREEN_PIN, RED_PIN)


def signal_handler(signal, frame):
    print('Setting {} low and exiting'.format(ALL_PINS))
    GPIO.output(ALL_PINS, GPIO.LOW)
    sys.exit(0)


def cycle_pin(pin, interval=0.1):
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(interval)

    GPIO.output(pin, GPIO.LOW)

signal.signal(signal.SIGINT, signal_handler)
GPIO.setmode(GPIO.BCM)
GPIO.setup(ALL_PINS, GPIO.OUT)

while True:
    cycle_pin(RED_PIN)
    cycle_pin(GREEN_PIN)
    cycle_pin(YELLOW_PIN)
    print('Cycled pins {}.'.format(ALL_PINS))
