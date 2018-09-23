#!/usr/bin/python
""" Python script to  check pool temp,level,acid level and filter PSI  """
# Can be run manually or via cron
__author__ = 'Richard J. Sears'
VERSION = "V3.4.6 (2018-09-23)"
# richard@sears.net

#TODO Put more thought into logging. Too much? Too little?


# Manage Imports
import sys
#sys.path.append('utilities')
sys.path.append('/var/www/utilities')
import pooldb  # Database information
import mysql.connector
from mysql.connector import errorcode
import time
import RPi.GPIO as GPIO  # Import GPIO Library
import ConfigParser
import serial
import subprocess
import datetime
import urllib2
import json
import httplib
from subprocess import call
import requests
import get_ph
import get_orp
import influx_data
from notifications import debug, verbose_debug, log, notify

config = ConfigParser.ConfigParser()
current_timestamp = int(time.time())


## Let's setup our GPIO stuff here
# Connected to GPIO 2 (Physical Pin 3) Builtin Resistor
manual_fill_button = 2

# The LED in the button is connected to GPIO 11 (Physical Pin 23)
manual_fill_button_led = 11

# Our relay for the sprinkler valve is on GPIO 17 (Physical Pin 11)
pool_fill_relay = 17

# Relay that controls power to the transformer that operates
# the sprinkler valve (Physical Pin 19)
pool_fill_transformer_relay = 26


# Acid level sensor pin here is tied to GPIO 14. The acid level sensor is
# a three wire connection with ground and 3.3V plus GPIO for detecting the
# level of the acid in our acid tank. It provides OK or LOW only, not a
# specific level in the tank.
acid_level_sensor_pin = 14

sprinkler_run_led = 5
pump_run_led = 13
system_run_led = 21
system_error_led = 16
pool_filling_led = 12
pool_fill_valve_disabled_pin = 3
pool_fill_valve_disabled_led = 4
pool_pump_running_pin = 19


# Setup our GPIO Pins
GPIO.setwarnings(False)  # Don't tell me about GPIO warnings.
GPIO.setmode(GPIO.BCM)  # Use BCM Pin Numbering Scheme
GPIO.setup(pool_fill_relay, GPIO.OUT)
GPIO.setup(pool_fill_transformer_relay, GPIO.OUT)
GPIO.setup(manual_fill_button_led, GPIO.OUT)  # Make LED  an Output
GPIO.setup(sprinkler_run_led, GPIO.OUT)
GPIO.setup(pump_run_led, GPIO.OUT)
GPIO.setup(system_run_led, GPIO.OUT)
GPIO.setup(system_error_led, GPIO.OUT)
GPIO.setup(pool_filling_led, GPIO.OUT)
GPIO.setup(pool_fill_valve_disabled_pin, GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(pool_fill_valve_disabled_led, GPIO.OUT)
GPIO.setup(acid_level_sensor_pin, GPIO.IN)
GPIO.setup(pool_pump_running_pin, GPIO.IN,pull_up_down=GPIO.PUD_UP)


# Setup to read and write to a status file:
def read_pool_sensor_status_values(file, section, status):
    log("DEBUG", "read_pool_sensor_values_called() with {}, {}, {}".format(file, section, status))
    pathname = '/var/www/' + file
    config.read(pathname)
    current_status = config.get(section, status)
    return current_status

def update_pool_sensor_status_values(file, section, status, value):
    log("DEBUG", "update_pool_sensor_values_called() with {}, {}, {}, {}".format(file, section, status, value))
    pathname = '/var/www/' + file
    config.read(pathname)
    cfgfile = open(pathname, 'w')
    config.set(section, status, value)
    config.write(cfgfile)
    cfgfile.close()


# Do we have internet access? This functions checks for internet access. We then use this to determine
# which database server we will be using (eventually). If we do not have internet access, we (currently) cannot run
# this system until I rewrite the code to reference local servers as opposed to remote servers.
#TODO Add local DB servers so this system will run without internet access.
def check_internet():
    log("DEBUG", "check_internet() Started")
    verbose_debug("check_internet() Started")
    check_url = pooldb.check_url
    conn = httplib.HTTPConnection(check_url, timeout=3)
    try:
        conn.request("HEAD", "/")
        conn.close()
        debug("We have Internet Access!")
        verbose_debug("check_internet() Completed")
        log("DEBUG", "check_internet(): We have Internet Access")
        log("DEBUG", "check_internet() Completed")
        return True
    except:
        conn.close()
        debug("We 'DO NOT' have Internet Access!")
        debug("EXITING: Will try again on the next run!")
        verbose_debug("check_internet() Completed")
        log("WARN", "check_internet(): We 'DO NOT' have Internet Access. Exiting!")
        log("WARN", "check_internet() Completed with Errors. System Exit")
        exit()  # At "this" point we cannot run without internet, so just throw the error and exit.
                # We need to change DB setup to allow it to run without internet!!

# This is the setup to our MightyHat (lowpowerlabs.com). You can disable this
# function if you are not using the MightyHat. Remove it here as well as in
# def main() below. If you leave it, error handling should catch it and allow
#the rest of the script to continue.
#
# Error handling in case USB port wrong or fails to open or no MightyHat -
# at least code will continue to run in either case. Does not effect outcome
# of program. MightyHat is informational display only.
def mightyhat_serial_setup():
    log("DEBUG", "mightyhat_serial_setup() - Started")
    verbose_debug("mightyhat_serial_setup() - Started")
    #TODO Finish setting up MightyHat message management
    """ Setup Serial communication with Mightyhat LCD screen. """
    try:
        global ser
        ser = serial.Serial(
            port='/dev/ttyAMA0',
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1)
    except Exception as error:
        debug("EXCEPTION: mightyhat_serial_setup()")
        log("WARN", "EXCEPTION: mightyhat_serial_setup()")
        log("WARN", error)
        debug(type(error))
        debug(error)
    verbose_debug("mightyhat_serial_setup()  - Completed")
    log("DEBUG", "mightyhat_serial_setup() - Completed")

# LED Blinking
def blink_led(pin, numtimes, speed):
    for i in range(0, numtimes):
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed)

# LED Control - ON/OFF = True/False
def led_control(led, onoff):
    """ Function to turn LEDs on and off. """
    if onoff == "True":
        GPIO.output(led, True)
    elif onoff == "False":
        GPIO.output(led, False)

# Here is where we convert our resistance level from our eTape to a percentage
# for our web interface:
def get_pool_level_percentage(level):
      if (level > pooldb.pool_resistance_ok_level):
              return (100 - (level - pooldb.pool_resistance_ok_level))
      return 100

# Convert our battery voltages from various sensors to percentages
# for web interface
def get_battery_percentage(voltage):
    global batt_level
    if voltage >= 3.2:
        batt_level = 100
    elif voltage >= 3.0 < 3.2:
        batt_level = 87
    elif voltage >= 2.7 < 3.0:
        batt_level = 67
    elif voltage >= 2.5 < 2.7:
        batt_level = 53
    elif voltage >= 2.2 < 2.5:
        batt_level = 33
    else:
        batt_level = 20
    return batt_level

# We are utilizing pump control software from Russell Goldin
# (https://github.com/tagyourit) to manage our Pentair Variable Speed pump and
# this is where we check to make sure that it is running so we can use it. If it
# is not running, then we get some information like wattage from our energy
# management functions.
def check_pump_control_url():
    verbose_debug("check_pump_control_url() Started")
    log("DEBUG", "check_pump_control_url() Started")
    check_url = pooldb.PUMP_DATA_TEST_URL
    conn = httplib.HTTPConnection(check_url, timeout=3)
    try:
        conn.request("HEAD", "/")
        conn.close()
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active", True)
        verbose_debug("Pump Control System - Online")
        verbose_debug("check_pump_control_url() Completed")
        log("DEBUG", "Pump Control System - Online")
        log("DEBUG", "check_pump_control_url() Completed")
        return True
    except:
        conn.close()
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active", False)
        verbose_debug("check_pump_control_url() Completed")
        debug("Pump Control System - Offline")
        log("DEBUG", "Pump Control System - Offline")
        log("DEBUG", "check_pump_control_url() Completed")
        return False


# Function to retrieve json data from pump control software
# See https://github.com/tagyoureit/nodejs-poolController
# Exception handling due to URL request.
def get_pump_data(key):
    verbose_debug("get_pump_data() Started")
    verbose_debug("get_pump_data() called with '{}' ".format(key))
    log("DEBUG", "get_pump_data() called with '{}' ".format(key))
    global json
    global pump_data
    try:
        req = urllib2.Request(pooldb.PUMP_DATA_URL)
        opener = urllib2.build_opener()
        f = opener.open(req)
        json = json.loads(f.read())
        pump_data = json["pump"]["1"][key]
        verbose_debug("get_pump_data() returned {}".format(pump_data))
        log("DEBUG", "get_pump_data() returned {}".format(pump_data))
        verbose_debug("get_pump_data()  - Completed")
        log("DEBUG", "get_pump_data() - Completed")
        return pump_data
    except Exception as error:
        debug("EXCEPTION: get_pump_data()")
        log("WARN", "EXCEPTION: get_pump_data()")
        log("WARN", error)
        debug(type(error))
        debug(error)
        verbose_debug("get_pump_data()  - Completed with EXCEPTION")
        log("DEBUG", "get_pump_data() - Completed with EXCEPTION")

# This function is only called externally by our Flask web template
# so there is no screen debugging outputted as it will never be seen, however
# we leave it in in case we are running flask in debug mode we will see the messages.
def pump_control(command):
    pump_control_active = check_pump_control_url()
    pump_program_running = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running")
    pump_control_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_notifications")
    if pump_control_active:
        try:
            if command == "START":
                urllib2.urlopen(pooldb.PUMP_START_URL)
                update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                debug("pump_control() called with START command")
                log("INFO","pump_control() called with START command")
                notify("pump_control_notifications", "Your pool pump has been started.", "Your pool pump has been started.")
            elif command == "PROGRAM_1":
                if pump_program_running == "program_1":
                    pass
                else:
                    urllib2.urlopen(pooldb.PUMP_PROGRAM1_URL)
                    update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                    debug("pump_control() called with PROGRAM 1 (15 GPM) command")
                    log("INFO", "pump_control() called with PROGRAM 1 (15 GPM) command")
                    notify("pump_control_notifications", "Your pool pump has been set to 15 GPM.", "Your pool pump has been set to 15 GPM.")
            elif command == "PROGRAM_2":
                if pump_program_running == "program_2":
                    pass
                else:
                    urllib2.urlopen(pooldb.PUMP_PROGRAM2_URL)
                    update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                    debug("pump_control() called with PROGRAM 2 (20 GPM) command")
                    log("INFO",
                        "pump_control() called with PROGRAM 2 (20 GPM) command")
                    notify("pump_control_notifications", "Your pool pump has been set to 20 GPM.",
                           "Your pool pump has been set to 20 GPM.")
            elif command == "PROGRAM_3":
                if pump_program_running == "program_3":
                    pass
                else:
                    urllib2.urlopen(pooldb.PUMP_PROGRAM3_URL)
                    update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                    debug("pump_control() called with PROGRAM 3 (30 GPM) command")
                    log("INFO",
                        "pump_control() called with PROGRAM 3 (30 GPM) command")
                    notify("pump_control_notifications","Your pool pump has been set to 30 GPM.",
                           "Your pool pump has been set to 30 GPM.")
            elif command == "PROGRAM_4":
                if pump_program_running == "program_4":
                    pass
                else:
                    urllib2.urlopen(pooldb.PUMP_PROGRAM4_URL)
                    update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                    debug("pump_control() called with PROGRAM 4 (50 GPM) command")
                    log("INFO",
                        "pump_control() called with PROGRAM 4 (50 GPM) command")
                    notify("pump_control_notifications", "Your pool pump has been set to 50 GPM.",
                           "Your pool pump has been set to 50 GPM.")
            else:
                urllib2.urlopen(pooldb.PUMP_STOP_URL)
                update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", False)
                debug("pump_control() called with STOP command")
                log("INFO", "pump_control() called with STOP command")
                notify("pump_control_notifications", "Your pool pump has been stopped.",
                       "Your pool pump has been stopped.")
        except Exception as error:
            debug("EXCEPTION: pump_control()")
            log("WARN", "EXCEPTION: pump_control()")
            log("WARN", error)
            debug(type(error))
            debug(error)
            verbose_debug("pump_control()  - Completed with EXCEPTION")
            log("DEBUG", "pump_control() - Completed with EXCEPTION")
    else:
        pass

# Without the pump control software we have no way to get the GPM of the pump - so return 0 GPM
def get_pump_gpm():
    verbose_debug("get_pump_gpm() Started")
    log("DEBUG", "get_pump_gpm() Started")
    pump_control_active = check_pump_control_url()
    if pump_control_active:
        if pooldb.PUMP_DATA == "NODEJS":
            try:
                global gpm
                global pump_gpm
                req = urllib2.Request(pooldb.PUMP_DATA_URL)
                opener = urllib2.build_opener()
                g = opener.open(req)
                gpm = json.loads(g.read())
                pump_gpm = gpm["pump"]["1"]["gpm"]
                update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_gpm", pump_gpm)
                log("INFO", "get_pump_gpm() reports Current GPM: {}".format(pump_gpm))
                log("DEBUG", "get_pump_gpm() Completed")
                debug("Current GPM: {}".format(pump_gpm))
                verbose_debug("get_pump_gpm() Completed")
                return pump_gpm
            except Exception as error:
                debug("EXCEPTION: get_pump_gpm()")
                log("WARN", "EXCEPTION: get_pump_gpm()")
                log("WARN", error)
                debug(type(error))
                debug(error)
                verbose_debug("get_pump_gpm()  - Completed with EXCEPTION")
                log("DEBUG", "get_pump_gpm() - Completed with EXCEPTION")
                update_pool_sensor_status_values("pool_sensor_status","pump_status", "pump_gpm",pump_gpm)
                log("DEBUG", "get_pump_gpm() FAILED: Current GPM set to: {}".format(pump_gpm))
                debug("get_pump_gpm() FAILED: Current GPM set to: {}".format(pump_gpm))
                return pump_gpm
        else:
            pump_gpm = 0
            update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_gpm", pump_gpm)
            verbose_debug("get_pump_gpm()  - Completed - No Pump Control Software Configured.")
            log("DEBUG", "get_pump_gpm() - Completed - No Pump Control Software Configured.")
            log("DEBUG", "get_pump_gpm() reports Current GPM: {} - No Pump Control Software Configured.".format(pump_gpm))
            debug("Current GPM: {} - No Pump Control Software Configured.".format(pump_gpm))
            log("INFO", "get_pump_gpm() reports Current GPM: {} - No Pump Control Software Configured".format(pump_gpm))
            return pump_gpm
    else:
        pump_gpm = 0
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_gpm", pump_gpm)
        log("DEBUG", "get_pump_gpm() - Pump Control Software not active or not responding, pump_gpm set to '0'.")
        debug("get_pump_gpm() - Pump Control Software not active or not responding, pump_gpm set to '0'.")
        log("INFO", "get_pump_gpm() reports Current GPM: {}".format(pump_gpm))
        verbose_debug("get_pump_rpm() Completed")
        return pump_gpm

# Without the pump control software we have no way to get the RPM of the pump - so return 0 RPM
def get_pump_rpm():
    verbose_debug("get_pump_rpm() Started")
    log("DEBUG", "get_pump_rpm() Started")
    pump_control_active = check_pump_control_url()
    if pump_control_active:
        if pooldb.PUMP_DATA == "NODEJS":
            try:
                global rpm
                global pump_rpm
                req = urllib2.Request(pooldb.PUMP_DATA_URL)
                opener = urllib2.build_opener()
                f = opener.open(req)
                rpm = json.loads(f.read())
                pump_rpm = rpm["pump"]["1"]["rpm"]
                update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_rpm", pump_rpm)
                log("INFO", "get_pump_rpm() reports Current RPM: {}".format(pump_rpm))
                log("DEBUG", "get_pump_rpm() Completed")
                debug("Current RPM: {}".format(pump_rpm))
                return pump_rpm
            except Exception as error:
                debug("EXCEPTION: get_pump_rpm()")
                debug(type(error))
                debug(error)
                log("WARN", "EXCEPTION: get_pump_rpm()")
                log("WARN", error)
                verbose_debug("get_pump_rpm()  - Completed with EXCEPTION")
                log("DEBUG", "get_pump_rpm() - Completed with EXCEPTION")
                update_pool_sensor_status_values("pool_sensor_status","pump_status", "pump_rpm",pump_rpm)
                log("DEBUG", "get_pump_gpm() FAILED: Current GPM set to: {}".format(pump_rpm))
                debug("get_pump_rpm() FAILED: Current GPM set to: {}".format(pump_rpm))
                return pump_rpm
        else:
            pump_rpm = 0
            update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_rpm", pump_rpm)
            verbose_debug("get_pump_rpm()  - Completed - No Pump Control Software Configured.")
            log("DEBUG", "get_pump_rpm() - Completed - No Pump Control Software Configured.")
            log("DEBUG", "get_pump_rpm() reports Current RPM: {} - No Pump Control Software Configured.".format(pump_rpm))
            debug("Current RPM: {} - No Pump Control Software Configured.".format(pump_rpm))
            log("INFO", "get_pump_rpm() reports Current RPM: {} - No Pump Control Software Configured".format(pump_rpm))
            return pump_rpm
    else:
        pump_rpm = 0
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_rpm", pump_rpm)
        log("DEBUG", "get_pump_rpm() - Pump Control Software not active or not responding, pump_rpm set to '0'.")
        debug("get_pump_rpm() - Pump Control Software not active or not responding, pump_rpm set to '0'.")
        verbose_debug("get_pump_rpm() Completed")
        log("DEBUG", "get_pump_rpm() Completed")
        return pump_rpm

# see function is_pool_pump_running(). We do not record our pump wattage here, this is just a function to read
# this information via json from our pump control software if it is running.
def get_pump_watts():
    verbose_debug("get_pump_watts() Started")
    log("DEBUG", "get_pump_watts() Started")
    global watts 
    global pump_watts
    try:
        req = urllib2.Request(pooldb.PUMP_DATA_URL)
        opener = urllib2.build_opener()
        f = opener.open(req)
        watts = json.loads(f.read())
        pump_watts = watts["pump"]["1"]["watts"]
        log ("INFO", "get_pump_watts() reports Current Watts: {}".format(pump_watts))
        log("DEBUG", "get_pump_watts() Completed")
        return pump_watts
    except Exception as error:
                debug("EXCEPTION: get_pump_rpm()")
                debug(type(error))
                debug(error)
                log("WARN", "EXCEPTION: get_pump_rpm()")
                log("WARN", error)
                verbose_debug("get_pump_rpm()  - Completed with EXCEPTION")
                log("DEBUG", "get_pump_rpm() - Completed with EXCEPTION")
                update_pool_sensor_status_values("pool_sensor_status","pump_status", "pump_rpm",pump_rpm)
                log("DEBUG", "get_pump_gpm() FAILED: Current GPM set to: {}".format(pump_rpm))
                debug("get_pump_rpm() FAILED: Current GPM set to: {}".format(pump_rpm))
                return pump_rpm

# Called by our web interface to control Pump Control Software
def pump_control_software(startstop):
    log("DEBUG", "pump_control_software() Started")
    pump_control_software_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_software_notifications")
    if startstop == "START":
        call(["pm2", "start", "index"])
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active", True)
        log("INFO",
            "pump_control_software() called with 'START' command")
        notify("pump_control_software_notifications",
               "Pump Control Software",
               "Your pump control software has started.")
        log("DEBUG", "pump_control_software() Completed")
    else:
        call(["pm2", "stop", "index"])
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active", False)
        log("INFO",
            "pump_control_software() called with 'STOP' command")
        notify("pump_control_software_notifications",
               "Pump Control Software",
               "Your pump control software has been stopped.")
        log("DEBUG", "pump_control_software() Completed")


#TODO Add sprinkler notifications to web interface and notification system
def get_sprinkler_status():
    """ Function to determine if our sprinklers are currently running. """
    debug("get_sprinkler_status() Started")
    if pooldb.sprinkler_type == "Timer":
        SprinklerStart = int(400)
        SprinklerStop = int(1000)

        current_military_time = int(datetime.datetime.now().strftime('%H%M'))

        if SprinklerStart < current_military_time < SprinklerStop:
            sprinklers_on = "True"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", True)
            led_control(sprinkler_run_led, "True")
            update_pool_sensor_status_values("pool_sensor_status", "led_status", "sprinkler_run_led", True)
            debug("Sprinklers are running via TIMER mode.")
            log("DEBUG", "Sprinklers are running via TIMER mode.")
            debug("Sprinkler Run LED should be ON. This is a BLUE LED.")
            log("DEBUG", "Sprinkler Run LED should be ON. This is a BLUE LED.")
        else:
            sprinklers_on = "False"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", False)
            led_control(sprinkler_run_led, "False")
            update_pool_sensor_status_values("pool_sensor_status", "led_status", "sprinkler_run_led", False)
            debug("Sprinklers are not running (TIMER)")
            log("DEBUG", "Sprinklers are not running via TIMER mode.")
            debug("Sprinkler Run LED should be off. This is a BLUE LED.")
            log("DEBUG", "Sprinkler Run LED should be off. This is a BLUE LED.")
        return sprinklers_on
    else:
        debug("Checking to see if sprinklers are running via subprocess call (RACHIO).")
        log("DEBUG", "get_sprinkler_status() called via subprocess")
        output = subprocess.check_output(pooldb.rachio_url, shell=True)
        if output == "{}":
            sprinklers_on = "False"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", False)
            led_control(sprinkler_run_led, "False")
            update_pool_sensor_status_values("pool_sensor_status", "led_status", "sprinkler_run_led", False)
            debug("Sprinklers are not running (RACHIO)")
            log("DEBUG", "Sprinklers are not running via RACHIO mode.")
            debug("Sprinkler Run LED should be off. This is a BLUE LED.")
            log("DEBUG", "Sprinkler Run LED should be off. This is a BLUE LED.")
        else:
            sprinklers_on = "True"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", True)
            update_pool_sensor_status_values("pool_sensor_status", "led_status", "sprinkler_run_led", True)
            debug("Sprinklers are running (RACHIO)")
            log("DEBUG", "Sprinklers are running via RACHIO mode.")
            led_control(sprinkler_run_led, "True")
            debug("Sprinkler Run LED should be ON. This is a BLUE LED.")
            log("DEBUG", "Sprinkler Run LED should be ON. This is a BLUE LED.")
    debug("get_sprinkler_status() Completed.")
    log("DEBUG", "get_sprinkler_status Completed")
    return sprinklers_on


## Here is where we get our pH reading if we have a probe installed.
## In order to get an accurate pH reading the way the sensors are
## installed, we must have the pool pump running. Here is where we
## check to see if the pool pump is running. If it is, we get the
## pH reading, if it is not, we do nothing but log the fact the pump
## is not running.

def get_ph_reading():
    log("DEBUG", "get_ph_reading() Started")
    pool_pump_running = read_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led" )
    if pool_pump_running == "True":
        if pooldb.temp_probe == "Yes":
            pool_temp = float(read_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_current_temp" ))
            ph_value = float(get_ph.get_current_ph_with_temp(pool_temp))
        else:
            ph_value = float(get_ph.get_current_ph_no_temp())
        debug("Current pH is: {}".format(ph_value))
        influx_data.write_data("pH", ph_value)
        influx_data.write_data("pool_temp", pool_temp)
        if pooldb.emoncms_server1 == "Yes":
            res = requests.get("http://" + pooldb.server1 + "/" + pooldb.emoncmspath1 + "/input/post?&node=" + str(
                pooldb.ph_node) + "&csv=" + ph_value + "&apikey=" + pooldb.apikey1)
            log("DEBUG", "Sent current pH Value of {} to Emoncms Server 1".format(ph_value))
            debug("Sent current pH Value of {} to Emoncms Server 1".format(ph_value))
        if pooldb.emoncms_server2 == "Yes":
            res = requests.get("https://" + pooldb.server2 + "/" + pooldb.emoncmspath2 + "/input/post?&node=" + str(
                pooldb.ph_node) + "&csv=" + ph_value + "&apikey=" + pooldb.apikey2)
            log("DEBUG",
                "Sent current pH Value of {} to Emoncms Server 2".format(
                    ph_value))
            debug("Sent current pH Value of {} to Emoncms Server 2".format(
                ph_value))
        update_pool_sensor_status_values("pool_sensor_status", "pool_chemicals", "pool_current_ph", ph_value)
        log("DEBUG", "get_ph_reading() Completed")
    else:
        log("INFO", "Pool Pump is NOT running, cannot get accurate pH reading!")
        debug("Pool pump is NOT running, cannot get accurate pH reading!")
        log("DEBUG", "get_ph_reading() Completed")


## If we have an ORP Probe installed (Atlas Scientific USB) set it up here.
## In order to get an accurate ORP reading the way the sensors are
## installed, we must have the pool pump running. Here is where we
## check to see if the pool pump is running. If it is, we get the
## ORP reading, if it is not, we do nothing but log the fact the pump
## is not running.

def get_orp_reading():
    log("DEBUG", "get_orp_reading() Started")
    pool_pump_running = read_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led" )
    if pool_pump_running == "True":
        orp_value = float(get_orp.get_current_orp())
        influx_data.write_data("orp", orp_value)
        debug("Current ORP is: {}".format(orp_value))
        if pooldb.emoncms_server1 == "Yes":
            res = requests.get("http://" + pooldb.server1 + "/" + pooldb.emoncmspath1 + "/input/post.json?&node=" + str(
                pooldb.orp_node) + "&csv=" + orp_value + "&apikey=" + pooldb.apikey1)
            log("DEBUG",
                "Sent current ORP Value of {} to Emoncms Server 1".format(
                    orp_value))
            debug("Sent current ORP Value of {} to Emoncms Server 1".format(
                orp_value))
        if pooldb.emoncms_server2 == "Yes":
            res = requests.get("https://" + pooldb.server2 + "/" + pooldb.emoncmspath2 + "/input/post.json?&node=" + str(
                pooldb.orp_node) + "&csv=" + orp_value + "&apikey=" + pooldb.apikey2)
            log("DEBUG",
                "Sent current ORP Value of {} to Emoncms Server 2".format(
                    orp_value))
            debug("Sent current ORP Value of {} to Emoncms Server 2".format(
                orp_value))
        update_pool_sensor_status_values("pool_sensor_status", "pool_chemicals", "pool_current_orp", orp_value)
        log("DEBUG", "get_orp_reading() Completed")
    else:
        log("INFO", "Pool Pump is NOT running, cannot get accurate ORP reading!")
        debug("Pool pump is NOT running, cannot get accurate ORP reading!")
        log("DEBUG", "get_orp_reading() Completed")

# Track total gallons added to pool during fill times
def get_gallons_total():
    log("DEBUG", "get_gallons_total() Started")
    cnx = mysql.connector.connect(user=pooldb.username,
                                  password=pooldb.password,
                                  host=pooldb.servername,
                                  database=pooldb.emoncms_db)
    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_gallons_total))

    for data in cursor:
        pool_gallons_total = int("%1.0f" % data)
        cursor.close()
        debug("Total Gallons: {}".format(pool_gallons_total))
        log("DEBUG", "get_gallons_total() returned: Total Gallons: {}".format(pool_gallons_total))
    cnx.close()
    log("DEBUG", "get_gallons_total() Completed")
    return pool_gallons_total

def calculate_current_fill_gallons():
    log("DEBUG", "calculate_current_fill_gallons() Started")
    fill_gallons_start = get_gallons_total()
    fill_gallons_stop = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons","gallons_stop")
    current_fill_gallons = int(fill_gallons_start) - int(fill_gallons_stop)
    update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", current_fill_gallons)
    log("DEBUG", "calculate_current_fill_gallons() returned: Current Fill Gallons: {}".format(current_fill_gallons))
    log("DEBUG", "calculate_current_fill_gallons() Completed")
    return current_fill_gallons

def calculate_gallons_used():
    log("DEBUG", "calculate_gallons_used() Started")
    gallons_start = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons","gallons_start")
    gallons_stop = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons","gallons_stop")
    gallons_used = int(gallons_stop) - int(gallons_start)
    update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_last_fill", gallons_used)
    log("DEBUG", "calculate_gallons_used() returned: Gallons Used: {}".format(gallons_used))
    log("DEBUG", "calculate_gallons_used() Completed")
    return gallons_used


# TODO - Complete pfv_function, add notification via PB once until PFV reenabled!
# TODO - Update logging for pfv_disable function
def pfv_disabled():
    pool_fill_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_notifications")
    # TODO Complete and test pfv_disabled() function
    """ Function to determine if our PFV has been manually disabled. """
    if DEBUG == "True":
        print("Starting pfv_disabled().")
    # Let take a quick look at the switch that controls our fill valve. Has
    # it been disabled? If so, send a notification
    # and log the error.
    pool_fill_valve_disabled = GPIO.input(pool_fill_valve_disabled_pin)
    if pool_fill_valve_disabled == True:
        led_control(pool_fill_valve_disabled_led, "True")
        if PUSHBULLET == "True" and pool_fill_notifications == "True":
            send_push_notification("Pool Fill Valve DISABLED", "Your pool fill valve has been DISABLED. Pool will not fill.")
    if DEBUG == "True":
        print("Completed pfv_disabled() function")

# Pool_Fill_Valve controls pool sprinkler relay as well as pool sprinkler
# transformer relay.
def pool_fill_valve(openclose):
    current_timestamp = int(time.time())
    if openclose == "OPEN":
       sprinkler_status = get_sprinkler_status()
       pool_level_sensor_ok = read_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok")
       if sprinkler_status == "True":
           debug("Sprinklers are running, we cannot fill the pool at this time, we will try again later.")
           log("INFO", "Sprinklers are running, we cannot fill the pool at this time, we will try again later.")
           pass
       elif pool_level_sensor_ok == "False":
           debug("There is a problem with your pool level sensor and we cannot fill the pool.")
           log("WARN", "There is a problem with a pool level sensor and we cannot fill the pool.")
           notify("pool_fill_notifications", "Unable to Refill Pool!", "There is a problem with your pool level sensor. We are unable to fill the pool.")
           pass
       else:
           gallons_start = get_gallons_total()
           update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_start", gallons_start)
           update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", True)
           update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time", current_timestamp)
           GPIO.output(pool_fill_transformer_relay, True)  # Turns on the Sprinkler Transformer
           GPIO.output(pool_fill_relay, True)  # Turns on the sprinkler valve
           led_control(pool_filling_led, "True") # Turns on the pool filling blue LED
           update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", True)
           log("Pool is low and is automatically refilling.")
           debug("""pool_fill_valve called with OPEN command\n
                    pool_fill_transformer_relay is now powered and pool transformer is now ACTIVE\n
                    pool_fill_relay is now powered and sprinkler valve solenoid is now powered\n
                    Both relays should now be active and Sprinkler valve should be open and water should be running\n
                    Pool Filling LED should be on. This is a BLUE LED""")
           notify("pool_fill_notifications", "Your pool is low and is automatically filling", "Your pool is low and is automatically filling.")
    elif openclose == "CLOSE":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        gallons_stop = get_gallons_total()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_stop", gallons_stop)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        calculate_gallons_used()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", 0)
        log("INFO", "Your pool is done refilling.")
        debug("""pool_fill_valve called with CLOSE command\n
                pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered\n
                pool_fill_transformer_relay is now powered off and pool transformer is now OFF\n
                Both relays should no longer be active. Sprinkler valve and transformer are now off\n
                Pool Filling LED should be OFF. This is a BLUE LED""")
        notify("pool_fill_notifications", "Your pool is done automatically filling", "Your pool is done automatically filling.")
    elif openclose == "WEBCLOSE":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        gallons_stop = get_gallons_total()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_stop", gallons_stop)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        calculate_gallons_used()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", 0)
        log("INFO", "Auto Fill terminated by WEB request.")
        debug("""pool_fill_valve called with WEBCLOSE command\n
                pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered\n
                pool_fill_transformer_relay is now powered off and pool transformer is now OFF\n
                Both relays should no longer be active. Sprinkler valve and transformer are now off\n
                Pool Filling LED should be OFF. This is a BLUE LED""")
        notify("pool_fill_notifications", "Pool Auto Fill Terminated by Web Request", "Your swimming pool has stopped filling due to a web request")
    elif openclose == "CRITICALCLOSE":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False")  # Turns off the pool filling blue LED
        gallons_stop = get_gallons_total()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_stop", gallons_stop)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        led_control(system_error_led, "True") # Turns on the System Error LED
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_error_led", True)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        calculate_gallons_used()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", 0)
        log("WARN", "Pool Fill CRITICAL stop!")
        debug("""pool_fill_valve called with CRITICAL CLOSE command\n
                pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered\n
                pool_fill_transformer_relay is now powered off and pool transformer is now OFF\n
                Both relays should no longer be active. Sprinkler valve and transformer are now off\n
                Pool Filling LED should be OFF. This is a BLUE LED\n
                System Error LED should be on. This is a RED LED""")
        notify("pool_fill_notifications", "Pool fill stopped with CRITICAL CLOSE", "You pool has stopped filling due to a CRITICAL STOP! Please check the system")
    elif openclose == "RESET":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        gallons_stop = get_gallons_total()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_stop", gallons_stop)
        calculate_gallons_used()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", 0)
        debug("pool_fill_valve called with RESET command")
        log("INFO", "pool_fill_valve() called with RESET command")
    elif openclose == "MANUAL_OPEN":
        log("INFO", "pool_fill_valve called with MANUAL_OPEN command")
        sprinkler_status = get_sprinkler_status()
        pool_level_sensor_ok = read_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok")
        if sprinkler_status == "True":
            blink_led(manual_fill_button_led, 7, 0.1)
            debug("Sprinklers are running, we cannot fill the pool at this time, we will try again later")
            log("INFO", "Sprinklers are running, we cannot fill the pool at this time, we will try again later")
            pass
        elif pool_level_sensor_ok == "False":
            blink_led(manual_fill_button_led, 7, 0.1)
            debug("INFO", "There is a problem with your pool level sensor and we cannot fill the pool")
            log("WARN", "There is a problem with your pool level sensor and we cannot fill the pool")
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", True)
            gallons_start = get_gallons_total()
            log("DEBUG", "pool_fill_valve MANUAL_OPEN gallons_start() = {} gallons".format(gallons_start))
            update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_start", gallons_start)
            update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time", current_timestamp)
            GPIO.output(pool_fill_transformer_relay, True)  # Turns on the Sprinkler Transformer
            GPIO.output(pool_fill_relay, True)  # Turns on the sprinkler valve
            led_control(pool_filling_led, "True")  # Turns on the pool filling blue LED
            led_control(manual_fill_button_led, "True")
            update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", True)
            update_pool_sensor_status_values("pool_sensor_status", "led_status", "manual_fill_button_led", True)
            notify("pool_fill_notifications", "Your Pool is MANUALLY Filling", "Your swimming pool is MANUALLY refilling.")
            debug("""MANUAL FILL BUTTON - pool_fill_valve called with OPEN command\n
                pool_fill_transformer_relay is now powered and pool transformer is now ACTIVE\n
                pool_fill_relay is now powered and sprinkler valve solenoid is now powered.\n
                Both relays should now be active and Sprinkler valve should be open and water should be running.\n
                Pool Filling LED should be on. This is a BLUE LED""")
            log("INFO", "Your pool is MANUALLY Filling.")
    elif openclose == "MANUAL_CLOSE":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(manual_fill_button_led, "False")
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        gallons_stop = get_gallons_total()
        log("DEBUG", "pool_fill_valve MANUAL_CLOSE gallons_stop() = {} gallons".format(gallons_stop))
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_stop", gallons_stop)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "manual_fill_button_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        gallons_used = calculate_gallons_used()
        log("DEBUG", "pool_fill_valve MANUAL_CLOSED calculate_gallons_used() = {} gallons".format(gallons_used))
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", 0)
        log("INFO", "Your pool is DONE manually filling.")
        notify("pool_fill_notifications", "Your Pool is DONE manually filling", "Your swimming pool is DONE manually refilling.")
        debug("""MANUAL FILL BUTTON - pool_fill_valve called with CLOSE command\n
            pool_fill_transformer_relay is now powered off and pool transformer is now OFF\n
            pool_fill_relay is now powered off and sprinkler valve solenoid is now off.\n
            Both relays should no longer be active and Sprinkler valve and transformer are now off.\n
            Pool Filling LED should be off. This is a BLUE LED""")

def get_main_power_readings():
    cnx = mysql.connector.connect(user=pooldb.username,
                                  password=pooldb.password,
                                  host=pooldb.servername,
                                  database=pooldb.emoncms_db)
    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.power_total_use))

    for data in cursor:
        power_total_use = int("%1.0f" % data)
        cursor.close()
        update_pool_sensor_status_values("pool_sensor_status", "power_solar", "total_current_power_utilization", power_total_use)
        debug("Total Current Power Utilization: {} watts".format(power_total_use))
        '''
        if DEBUG == "True":
            print("Total Current Power Utilization: %s watts" % power_total_use)
        '''
    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.power_importing))

    for data in cursor:
        power_importing = int("%1.0f" % data)
        cursor.close()
        update_pool_sensor_status_values("pool_sensor_status", "power_solar", "total_current_power_import", power_importing)
        debug("Total Current Power Import: {} watts".format(power_importing))
    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.power_solar))

    for data in cursor:
        power_solar = int("%1.0f" % data)
        cursor.close()
        update_pool_sensor_status_values("pool_sensor_status", "power_solar", "total_current_solar_production", power_solar)
        debug("Total Current Solar Production: {} watts".format(power_solar))
    cnx.close()

def check_pool_sensors():
    debug("Current unix datetime stamp is: {}".format(current_timestamp))
    cnx = mysql.connector.connect(user=pooldb.username,
                                  password=pooldb.password,
                                  host=pooldb.servername,
                                  database=pooldb.emoncms_db)
    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT time FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_level_table))

    for data in cursor:
        get_pool_level_sensor_time = int("%1.0f" % data)
        cursor.close()
        debug("Pool LEVEL sensor last updated at: {}".format(get_pool_level_sensor_time))

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_level_sensor_battery_table))

    for data in cursor:
        get_pool_level_sensor_battery_voltage = float("%1.2f" % data)
        cursor.close()
        level_voltage = get_battery_percentage(get_pool_level_sensor_battery_voltage)
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_level_batt_percentage", level_voltage)
        debug("Pool LEVEL sensor battery voltage is {} and battery percentage is {}".format(get_pool_level_sensor_battery_voltage, level_voltage))

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT time FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_temp_table))

    for data in cursor:
        get_pool_temp_sensor_time = int("%1.0f" % data)
        cursor.close()
        debug("Pool TEMP sensor last updated at: {}".format(get_pool_temp_sensor_time))

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_temp_sensor_battery_table))

    for data in cursor:
        get_pool_temp_sensor_battery_voltage = float("%1.2f" % data)
        cursor.close()
        temp_voltage = get_battery_percentage(get_pool_temp_sensor_battery_voltage)
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_temp_batt_percentage", temp_voltage)
        debug("Pool TEMP sensor battery voltage is {} and battery percentage is {}".format(get_pool_temp_sensor_battery_voltage, temp_voltage))

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pool_filter_psi_table))
    for data in cursor:
        get_pool_filter_psi = int("%1.0f" % data)
        influx_data.write_data("filter_psi", get_pool_filter_psi)
        cursor.close()
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "filter_current_psi", get_pool_filter_psi)
        debug("Pool FILTER Pressure is: {} PSI".format(get_pool_filter_psi))

    cnx.close()

    pool_level_sensor_time_delta = current_timestamp - get_pool_level_sensor_time
    pool_temp_sensor_time_delta = current_timestamp - get_pool_temp_sensor_time

    pool_level_timeout_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent")
    pool_level_lowvoltage_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent")
    pool_temp_timeout_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent")
    pool_temp_lowvoltage_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status","pool_temp_low_voltage_alert_sent")
    pool_filter_psi_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status","pool_filter_psi_alert_sent")
    pool_level_sensor_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings","pool_level_sensor_notifications")
    pool_temp_sensor_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings","pool_temp_sensor_notifications")
    pool_filter_psi_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings","pool_filter_psi_notifications")
    debug("Time dfference between last pool LEVEL sensor reading is: {} seconds.".format(pool_level_sensor_time_delta))
    debug("Time dfference between last pool TEMP sensor reading is: {} seconds.".format(pool_temp_sensor_time_delta))

    if pool_level_sensor_time_delta > pooldb.max_pool_level_sensor_time_delta:
        if pool_level_timeout_alert_sent == "True":
            pass
        else:
            log("WARN", "Pool LEVEL sensor timeout!")
            notify("pool_level_sensor_notifications", "Pool Level Sensor Timeout", "Your Pool Level Sensor has Timed Out!")
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", False)
        debug("* * * * WARNING * * * *\nPool LEVEL Sensor Timeout!")

    elif pool_level_sensor_time_delta < pooldb.max_pool_level_sensor_time_delta and pool_level_timeout_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", True)
        notify("pool_level_sensor_notifications", "Pool Level Sensor Timeout Has Ended", "Your Pool Level Sensor is Back Online!")

    elif get_pool_level_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
        if pool_level_lowvoltage_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", False)
            notify("pool_level_sensor_notifications", "Pool Level Sensor Low Voltage", "The battery is low in your pool level sensor.")
        debug("* * * * WARNING * * * *\nPool LEVEL Sensor Battery Voltage LOW!")

    elif get_pool_level_sensor_battery_voltage > pooldb.pool_level_sensor_low_voltage and pool_level_lowvoltage_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", True)
        log("INFO", "Pool LEVEL Sensor Battery level is Normal")

    elif pool_temp_sensor_time_delta > pooldb.max_pool_temp_sensor_time_delta:
        if pool_temp_timeout_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent", True)
            notify("pool_temp_sensor_notifications", "Pool Temp Sensor Timeout", "Your Pool Temp Sensor has Timed Out!")
        debug("* * * * WARNING * * * *\nPool TEMP Sensor Timeout!")

    elif pool_temp_sensor_time_delta < pooldb.max_pool_temp_sensor_time_delta and pool_temp_timeout_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent", False)
        notify("pool_temp_sensor_notifications", "Pool Temp Sensor Timeout Has Ended", "Your Pool Temp Sensor is Back Online!")

    elif get_pool_temp_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
        if pool_temp_lowvoltage_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_low_voltage_alert_sent", True)
            notify("pool_temp_sensor_notifications", "Pool Temp Sensor Low Voltage", "The battery is low in your pool temp sensor.")
        debug("* * * * WARNING * * * *\nPool TEMP Sensor Battery Voltage LOW!")

    elif get_pool_temp_sensor_battery_voltage > pooldb.pool_level_sensor_low_voltage and pool_temp_lowvoltage_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_low_voltage_alert_sent", False)
        log("INFO", "Pool TEMP Sensor Battery level is Normal")

    elif get_pool_filter_psi > pooldb.pool_filter_max_psi:
        if pool_filter_psi_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_filter_psi_alert_sent", True)
            notify("pool_filter_psi_notifications", "Pool Filter HIGH PSI", "It is time to BACK FLUSH your pool filter")
            log("WARN", "Pool filter PSI is HIGH!")
        debug("* * * * WARNING * * * *\nPool Filter Pressure HIGH - Backflush your filter!")

    elif get_pool_filter_psi < pooldb.pool_filter_max_psi_reset and pool_filter_psi_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_filter_psi_alert_sent", False)
        log("INFO", "Pool filter PSI is Normal")

    else:
        debug("Everything appears to be OK with the pool sensors!")


def get_pool_level_resistance():
    log("DEBUG", "get_pool_level_resistance() started")
    pool_manual_fill = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill")
    pool_fill_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_notifications")
    if pool_manual_fill == "True":
        current_timestamp = int(time.time())
        debug("Pool is Manually Filling - Automatic Fill disabled!")
        pool_fill_start_time = int(read_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time"))
        pool_fill_total_time = (current_timestamp - pool_fill_start_time) / 60
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", pool_fill_total_time)
        current_fill_gallons = calculate_current_fill_gallons()
        debug("Pool has been MANUALLY filling for {} minutes.".format(pool_fill_total_time))
        debug("Current gallons of water added to pool: {} gallons".format(current_fill_gallons))
        if pool_fill_total_time >= pooldb.max_pool_fill_time:
            update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
            notify("pool_fill_notifications", "Pool MANUAL Fill Critical Stop", "Your Pool has been MANUALLY filling too long. Critical Stop. Check System!")
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
            pool_fill_valve("CRITICALCLOSE")
            update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", False)
            debug("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
            log("WARN", "CRITICAL STOP!! Pool Max Fill Time Exceeded!")
        pass
    else:
        """ Function to get the current level of our pool from our MySQL DB. """
        cnx = mysql.connector.connect(user=pooldb.username,
                                      password=pooldb.password,
                                      host=pooldb.servername,
                                      database=pooldb.emoncms_db)
        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
            pooldb.pool_resistance_table))

        for data in cursor:
            get_pool_level_resistance_value = int("%1.0f" % data)
            cursor.close()
            pool_level_percentage = get_pool_level_percentage(get_pool_level_resistance_value)
            update_pool_sensor_status_values("pool_sensor_status", "pool_level", "pool_level_percentage", pool_level_percentage)
            influx_data.write_data("pool_level", pool_level_percentage)
            debug("pool_sensors: Pool Resistance is: {}".format(get_pool_level_resistance_value))
            debug("pool_sensors: Pool Level Percentage is {}".format(pool_level_percentage))
            debug("pooldb: Static Critical pool level resistance set at: {}".format(pooldb.pool_resistance_critical_level))
            debug("pooldb: Static Normal pool level resistance set at: {}".format(pooldb.pool_resistance_ok_level))
        cnx.close()

        pool_is_filling = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling")
        critical_stop = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop")
        current_timestamp = int(time.time())
        if get_pool_level_resistance_value >= pooldb.pool_resistance_critical_level:
            get_pool_level = "LOW"
            if pool_is_filling == "True":
                pool_fill_start_time = int(read_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time"))
                pool_fill_total_time = (current_timestamp - pool_fill_start_time) / 60
                update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", pool_fill_total_time)
                current_fill_gallons = calculate_current_fill_gallons()
                debug("Pool has been filling for {} minutes.\nCurrent number of gallons added to pool: {} gallons.".format(pool_fill_total_time, current_fill_gallons))
                if pool_fill_total_time >= pooldb.max_pool_fill_time:
                    update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
                    notify("pool_fill_notifications", "Pool Fill Critical Stop", "Your Pool has been filling too long. Critical Stop. Check System!")
                    update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
                    pool_fill_valve("CRITICALCLOSE")
                    debug("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                    log("WARN", "CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                pass
            else:
                if critical_stop == "True":
                    debug("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                    critical_stop_enabled_warning_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_enabled_warning_sent")
                    if critical_stop_enabled_warning_sent == "False":
                        notify("pool_fill_notifications", "Pool Fill Requested During Critical Stop", "Your Pool Fill is DISABLED due to Critical Stop and is LOW. Please check system!")
                        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_enabled_warning_sent", True)
                    pass
                else:
                    log("INFO", "Pool LEVEL is LOW!")
                    pool_autofill_active = read_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_autofill_active")
                    if pool_autofill_active == "True":
                        pool_fill_valve("OPEN")
                    else:
                        log("INFO", "Pool is low and needs filling, but pool_autofill has been disabled!")
                        debug("Pool is LOW but Autofill has been disable!")
                    debug("get_pool_level_resistance() returned pool_level = LOW")

        elif get_pool_level_resistance_value <= pooldb.pool_resistance_ok_level:
            get_pool_level = "OK"
            if pool_is_filling == "True":
                log("INFO", "Pool LEVEL is back to normal!")
                pool_fill_valve("CLOSE")
            debug("get_pool_level_resistance() returned pool_level = OK")
        else:
            if pool_is_filling == "True":
                pool_fill_start_time = int(read_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time"))
                pool_fill_total_time = (current_timestamp - pool_fill_start_time) / 60
                update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", pool_fill_total_time)
                current_fill_gallons = calculate_current_fill_gallons()
                debug("Pool has been filling for {} minutes.\nCurrent number of gallons added to pool: {} gallons.".format(pool_fill_total_time, current_fill_gallons))
                if pool_fill_total_time >= pooldb.max_pool_fill_time:
                    update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
                    notify("pool_fill_notifications", "Pool Fill Critical Stop", "Your Pool has been filling too long. Critical Stop. Check System!")
                    log("WARN", "Pool Fill Critical Stop - Your Pool has been filling too long. Critical Stop. Check System!")
                    update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
                    pool_fill_valve("CRITICALCLOSE")
                    debug("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                get_pool_level = "MIDWAY"
            else:
                get_pool_level = "MIDWAY"
        debug("Our Pool Level is {}.".format(get_pool_level))

def pool_pump_running_chemical():
    pool_pump_running_chemical = GPIO.input(pool_pump_running_pin)
    if pool_pump_running_chemical == False:
        debug("Pool Pump Running via Chemical Sensor Chamber: TRUE - PUMP IS RUNNING")
    else:
        debug("Pool Pump Running via Chemical Sensor Chamber: FALSE - PUMP IS OFF")

def acid_level():
    log("INFO", "acid_level() started")
    acid_level_ok = GPIO.input(acid_level_sensor_pin)
    if acid_level_ok == True:
        acid_level_status = read_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok")
        if acid_level_status == "False":
            update_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok", True)
            log("INFO", "Pool ACID Level is back to normal.")

        acid_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent")
        if acid_alert_sent == "True":
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent", False)
        debug("Acid Level - OK")

    else:
        pool_acid_level_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_acid_level_notifications")
        acid_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent")
        if acid_alert_sent == "True":
            acid_alert_sent_time = int(read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time"))
            acid_alert_sent_delta_time = (current_timestamp - acid_alert_sent_time) / 60
            time_to_next_acid_alert = (pooldb.pool_acid_alert_max_minutes - acid_alert_sent_delta_time)
            debug("Acid LOW Level Alert sent {} minuntes ago. Next Alert will be sent in {} minutes".format(acid_alert_sent_delta_time, time_to_next_acid_alert))

            if acid_alert_sent_delta_time >= pooldb.pool_acid_alert_max_minutes:
                notify("pool_acid_level_notifications", "Pool Acid Level is STILL LOW", "Your Acid Level is STILL LOW. Please refill!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time", current_timestamp)
                log("WARN", "Pool ACID Level STILL low. Alert sent again!")
            debug("Acid Level - LOW")

        else:
            debug("Acid Level - LOW")
            notify("pool_acid_level_notifications", "Pool Acid Level is LOW", "Your Acid Level is LOW. Please refill!")
            update_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok", False)
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time", current_timestamp)
            log("WARN", "Pool ACID Level is LOW!")

# TODO Why do I have this here? Maybe need to move other pool_temp info to call this function.
# Reads our pool temperature from MySQL DB
def get_pool_temp():
#    debug("get_pool_temp() Started")
    log("DEBUG", "get_pool_temp() Started")
    cnx = mysql.connector.connect(user=pooldb.username,
                                  password=pooldb.password,
                                  host=pooldb.servername,
                                  database=pooldb.emoncms_db)
    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.temp_probe_table))

    for (data) in cursor:
        get_pool_temp = float("%.2f" % data)
        cursor.close()
        cnx.close()
        pool_temp_c = float((get_pool_temp - 32) / 1.8)
        log("INFO", "get_pool_temp returned {}F and {}C".format(get_pool_temp, int(pool_temp_c)))
        debug("get_pool_temp returned {}F and {}C".format(get_pool_temp, int(pool_temp_c)))
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_current_temp", get_pool_temp)

    log("DEBUG", "get_pool_temp() Completed")
    return get_pool_temp



def check_system_status():
    current_military_time = datetime.datetime.now().strftime('%A %b %m, %Y  %H:%M:%S')
    update_pool_sensor_status_values("pool_sensor_status", "system_status", "current_military_time", current_military_time)
    system_reset_required = read_pool_sensor_status_values("pool_sensor_status", "system_status", "system_reset_required")
    critical_stop = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop")
    
    if system_reset_required == "True":
        pool_fill_control_reset_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_control_reset_notifications")
        log("INFO", "System Reset Requested")
        debug("System Reset has been Requested")
        # Make sure water is shut off
        pool_fill_valve("RESET")
        # Reset all LEDs to OFF
        led_control(pool_fill_valve_disabled_led, "False")
        led_control(sprinkler_run_led, "False")
        led_control(pump_run_led, "False")
        led_control(system_run_led, "False")
        led_control(pool_filling_led, "False")
        led_control(system_error_led, "False")
        led_control(manual_fill_button_led, "False")
        # Reset LED Status Values
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_fill_valve_disabled_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "sprinkler_run_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_run_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_error_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "manual_fill_button_led", False)
        # Reset fill status
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", False)
        # Rest Pool Fill Time
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        # Reset Notifications
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_enabled_warning_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_low_voltage_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_filter_psi_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_filling_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_time_warning_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pump_not_running_error_alert_sent", False)
        # Turn on our System Run LED now that everything has been reset back to normal.
        led_control(system_run_led, "True")
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_run_led", True)
        # Reset out Reset Required Value
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "system_reset_required", False)
        # Let me know the reset has been completed
        notify("pool_fill_control_reset_notifications", "Pool Fill Control RESET Complete", "Your Pool Fill Control has been reset to normal conditions.")
    else:
        log("INFO", "System Reset Status = No Reset Requested")
        debug("System Reset Status = No Reset Requested")
        led_control(system_run_led, "True")
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_run_led", True)
    if critical_stop == "True":
        log("WARN", "CRITICAL STOP DETECTED")
        log("WARN", "Please check all systems and set [system_reset_required = True] in config file and restart program.")
        log("WARN", "This will reset all systems and restart the program.")
        debug("""CRITICAL STOP DETECTED\n
                Please check all systems and set [system_reset_required = True] in config file and restart program.\n
                This will reset all systems and restart the program.""")

def is_pool_pump_running():
    """ Function to determine if our pool pump is running. This utilizes the pump_controrl_software and
    if the pump control software is not running it looks up how many watts are being  used by the pool
    panel. This should not e confused with the function pool_pump_running_ch() which utilizes GPIO 38 to detect
    if the pump is running utilizing a float switch connected to our pH/ORP chemical pot """
    debug("is_pool_pump_running() Started")
    if pooldb.PUMP_DATA == "NODEJS":
        pump_control_active = check_pump_control_url()
        if pump_control_active:
            pool_pump_running_watts = get_pump_watts()
        else:
            cnx = mysql.connector.connect(user=pooldb.username,
                                          password=pooldb.password,
                                          host=pooldb.servername,
                                          database=pooldb.emoncms_db)
            cursor = cnx.cursor(buffered=True)
            cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
                pooldb.pump_running_watts_table))

            for data in cursor:
                pool_pump_running_watts = int("%1.0f" % data)
                cursor.close()
    else:
        cnx = mysql.connector.connect(user=pooldb.username,
                                      password=pooldb.password,
                                      host=pooldb.servername,
                                      database=pooldb.emoncms_db)
        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
            pooldb.pump_running_watts_table))

        for data in cursor:
            pool_pump_running_watts = int("%1.0f" % data)
            cursor.close()
    debug("pool_pump_running_watts returned {} watts in use by the pump.".format(pool_pump_running_watts))
    update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_watts", pool_pump_running_watts)

    if pool_pump_running_watts > pooldb.max_wattage:
        led_control(pump_run_led, "True")
        pool_pump_running = "Yes"
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_running", True)
        debug("PUMP_RUN_LED should be ON. This is the YELLOW LED")
        pump_error_notification_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "pump_not_running_error_alert_sent")
        if pump_error_notification_sent == "True":
            log("INFO", "Pump Error CLEARED - Pump is currently programmed to be running and is running.")
            debug("Pump Error CLEARED - Pump currently programed to run and is running.")
            notify("pump_error_notifications", "Pump Error CLEARED - Pump is now Running!", "Your Pool Pump is currnetly programmed to run, and it is now running!")
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pump_not_running_error_alert_sent", False)
    else:
        led_control(pump_run_led, "False")
        pool_pump_running = "No"
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_running", False)
        pump_control_active = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active")
        if pump_control_active == "True":
            pump_program_running = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running")
            if pump_program_running in ("program_1", "program_2", "program_3", "program_4"):
                log("WARN", "Pump is currently programmed to be running but is NOT running. Check System!")
                debug("Pump Currently programed to run but is NOT running. Check System!")
                pump_error_notification_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "pump_not_running_error_alert_sent")
                if pump_error_notification_sent == "False":
                    notify("pump_error_notifications", "Pump Error - Pump Not Running!", "Your Pool Pump is currnetly programmed to run, but it is not running. Check your system!")
                    update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pump_not_running_error_alert_sent", True)
        debug("PUMP_RUN_LED should be OFF. This is the YELLOW LED")
    return pool_pump_running


# This is where we check to see if we can talk to our database. If not, stop and send notification.
def is_database_online():
    pool_database_error_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status","pool_database_error_alert_sent")
    pool_database_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_database_notifications")
    debug("is_database_online() Started")
    try:
        cnx = mysql.connector.connect(user=pooldb.username,
                                      password=pooldb.password,
                                      host=pooldb.servername,
                                      database=pooldb.emoncms_db,
                                      raise_on_warnings=True)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            log("WARN", "Database Error: Access Error - Check username or password.")
            if pool_database_error_alert_sent == "False":
                notify("pool_database_notifications", "Pool DB ACCESS DENIED Failure!", "Pool DB ACCESS DENIED Failure. Check your username/password and other access settings and reenable the system!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            debug("Database connection failure: Check your username and password!")
            exit()    
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            log("Database Error: Database does not exist.")
            if pool_database_error_alert_sent == "False":
                notify("pool_database_notifications", "Pool DB Connection Failure!", "Pool DB does not exist. Check your settings and reenable the system!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            debug("Database does not exist. Please check your settings.")
            exit()
        elif err.errno == errorcode.CR_CONN_HOST_ERROR:
            log("WARN", "Database Error: Cannot connect to MySQL database.")
            if pool_database_error_alert_sent == "False":
                notify("pool_database_notifications", "Pool DB Connection Failure!", "Cannot Connect to MySQL Server. Check your settings and reenable the system!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            debug("MySQL Server Error: Cannot connect to MySQL Server. Check connection and reset system.")
            exit()
        else:
            log("Database Error: Unknown Error.")
            if pool_database_error_alert_sent == "False":
                notify("pool_database_notifications", "Pool DB Connection Failure!", "Pool DB error. Check your settings and reenable the system!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            debug("Unknown database error, please check all of your settings.")
            exit()
    else:
        if pool_database_error_alert_sent == "True":
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", False)
            notify("pool_database_notifications", "Pool DB Back Online!", "Your Pool Database is back online. System is Normal!")
            cnx.close()
            pass
        else:
            cnx.close()
            pass


def get_current_ph():
    if pooldb.temp_probe == "Yes":
        pool_temp = float(read_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_current_temp" ))
        current_ph = get_ph.get_current_ph_with_temp(pool_temp)
    else:
        current_ph = get_ph.get_current_ph_no_temp()
    return current_ph

def get_current_orp():
    if pooldb.orp_probe == "Yes":
        current_orp = get_orp.get_current_orp()
        return current_orp
    else:
        pass

## The following three functions utilize the new Influx database engine(s) residing on 'scripts' located
## at our house as well as a second off-site server located in a datacenter in N. California. 
#TODO - Create database function tests to determine best database to use (MySQL or Influx). Default to local
# influx database, fallback to remote Influx database and then fall back to remote MySQL database. Fail if 
# no database connectivity or no internet connectivity for remote databases.

def get_current_solar():
    current_solar_results = influx_data.read_energy_data("electrical_monitoring", "energy", "XXX340_ch4_w")
    if current_solar_results == "None":
        current_solar = 0
    else:
        current_solar = (int(float(current_solar_results)) * -1) 
    return current_solar

def get_current_mains():
    current_mains_results = influx_data.read_energy_data("electrical_monitoring", "energy", "XXX340_ch20_w")
    if current_mains_results == "None":
        current_mains = 0
    else:
        current_mains = (int(float(current_mains_results))) 
    return current_mains

def calculate_total_power_consumption():
    current_mains = get_current_mains()
    current_solar = get_current_solar()
    total_consumption = (current_mains + current_solar)
    debug("Total current Power Utilizations is {0} watts. (InfluxDB)".format(total_consumption))
    debug("Total current Power Import is {0} watts. (InfluxDB)".format(current_mains))
    debug("Total current Solar Production is {0} watts. (InfluxDB)".format(current_solar))
    return total_consumption


# Here we go.......
def main():
    log("DEBUG", "pool_control_master started")
    check_internet()  # If we have no internet, immediately exit() and check again in 1 minute. 
    is_database_online()
    mightyhat_serial_setup()
    check_system_status()
    get_pool_temp()
    is_pool_pump_running()
    pool_pump_running_chemical()
    check_pool_sensors()
    get_sprinkler_status()
    get_pool_level_resistance()
    get_gallons_total()
    acid_level()
    get_main_power_readings()
    calculate_total_power_consumption() # Testing InfluxDB
    get_pump_gpm()
    get_pump_rpm()
    get_ph_reading()
    get_orp_reading()



if __name__ == '__main__':
    main()


