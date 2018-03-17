#!/usr/bin/python

## For use with pool_control_master.py
__author__ = 'Richard J. Sears'
VERSION = "V3.4 (2018-03-16)"
# richard@sears.net

# This is for use with Atlas Scientific pH board only.

import serial
import sys
import time
from serial import SerialException
usbport = '/dev/PH'

try:
    ser = serial.Serial(usbport, 38400, timeout=0)
except serial.SerialException as e:
    print "Error, ", e
    sys.exit(0)

def read_line():
        lsl = len('\r')
        line_buffer = []
        while True:
                next_char = ser.read(1)
                if next_char == '':
                        break
                line_buffer.append(next_char)
                if (len(line_buffer) >= lsl and
                                line_buffer[-lsl:] == list('\r')):
                        break
        return ''.join(line_buffer)

def read_lines():
        lines = []
        try:
                while True:
                        line = read_line()
                        if not line:
                                break
                                ser.flush_input()
                        lines.append(line)
                return lines

        except SerialException as e:
                print "Error, ", e
                return None

def send_cmd(cmd):
        """
        Send command to the Atlas Sensor.
        Before sending, add Carriage Return at the end of the command.
        :param cmd:
        :return:
        """
        buf = cmd + "\r"        # add carriage return
        try:
                ser.write(buf)
                return True
        except SerialException as e:
                print "Error, ", e
                return None

def get_current_ph_with_temp(current_temp):
#    send_cmd("RESPONSE,0")
    send_cmd("C,0")
    send_cmd("T,%d" % current_temp)
    send_cmd("R")
    time.sleep(1.3)
    lines = read_line()
    return lines

def get_current_ph_no_temp():
#    send_cmd("RESPONSE,0")
    send_cmd("C,0")
    send_cmd("R")
    time.sleep(1.3)
    lines = read_line()
    return lines

def main():
#    send_cmd("RESPONSE,0")
    send_cmd("C,0")
    send_cmd("R")
    time.sleep(1.3)
    lines = read_lines()
    print("No Temperature Calibration Performed:")
    for i in range(len(lines)):
            print lines[i]


if __name__ == '__main__':
        main()
