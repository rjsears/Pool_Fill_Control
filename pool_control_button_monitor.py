#!/usr/bin/env python

# Threaded Python App that monitors physical push button
# switch on RPi. This has been converted to MySQL mode
# on 02-16-2019.

__author__ = 'Richard J. Sears'
VERSION = "V3.5.0 (2019-02-16)"
# richard@sears.net


import sys
sys.path.append('/var/www/utilities')
import pigpio # http://abyz.co.uk/rpi/pigpio/python.html
import threading
import pool_control_master_db
from use_database import update_database, read_database


manual_fill_button = 2

def manual_fill_button_push(gpio, level, tick):
    pool_manual_fill = read_database("filling_status", "pool_manual_fill")
    if not pool_manual_fill:
        pool_control_master_db.pool_fill_valve("MANUAL_OPEN")
        update_database("filling_status", "pool_manual_fill", True)
    else:
        pool_control_master_db.pool_fill_valve("MANUAL_CLOSE")
        update_database("filling_status", "pool_manual_fill", False)


GLITCH=5000
pi = pigpio.pi()
pi.set_mode(manual_fill_button, pigpio.INPUT)
# Ignore edges shorter than GLITCH microseconds.
pi.set_glitch_filter(manual_fill_button, GLITCH)


def check_for_button():
    threading.Timer(10, check_for_button).start()

cb = pi.callback(manual_fill_button, pigpio.RISING_EDGE, manual_fill_button_push)

def main():
    check_for_button()

if __name__ == '__main__':
    main()
