#!/usr/bin/env python

__author__ = 'Richard J. Sears'
VERSION = "V3.3.02 (2018-02-20)"
# richard@sears.net

## pool_control_button_monitor.py
## 
## This is a threaded python app that monitors 
## a GPIO with a momentary push button attached.
## This is used for manually starting and stopping
## filling of the pool. This is also used by the
## flask web framework to manually start and stop
## filling the pool. 
##
## Please verify which pin you have your button on
## and configure as necessary. 
##
## THis REQUIRES pigpio and configparser for use. 


import time
import pigpio # http://abyz.co.uk/rpi/pigpio/python.html
import threading
import ConfigParser
import pool_control_master

config = ConfigParser.ConfigParser()

manual_fill_button = 2

# Setup to read and write to a status file:
def read_pool_sensor_status_values(file, section, status):
    pathname = '/var/www/' + file  # Set this directory to your working directory.
    config.read(pathname)
    current_status = config.get(section, status)
    return current_status

def update_pool_sensor_status_values(file, section, status, value):
    pathname = '/var/www/' + file  # Set this directory to your working directory.
    config.read(pathname)
    cfgfile = open(pathname, 'w')
    config.set(section, status, value)
    config.write(cfgfile)
    cfgfile.close()


def manual_fill_button_push(gpio, level, tick):
    current_timestamp = int(time.time())
    pool_manual_fill = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill")
    if pool_manual_fill == "False":
        if DEBUG:
            print ("Manual Pool Fill Started")
        pool_control_master.pool_fill_valve("MANUAL_OPEN")
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", True)
    else:
        if DEBUG:
            print ("Manual Pool Fill Stopped")
        pool_control_master.pool_fill_valve("MANUAL_CLOSE")
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", False)


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
