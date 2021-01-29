#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
FAN_PIN = 23
GPIO.setup(FAN_PIN, GPIO.OUT)
GPIO.output(FAN_PIN, True)

