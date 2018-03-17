#!/usr/bin/python
""" Python script to  check pool temp,level,acid level and filter PSI  """

# Can be run manually or via cron
__author__ = 'Richard J. Sears'
VERSION = "V3.4 (2018-03-16)"
# richard@sears.net

# Manage Imports
import pooldb  # Database information
import mysql.connector
from mysql.connector import errorcode
import time
import RPi.GPIO as GPIO  # Import GPIO Library
from pushbullet import Pushbullet
import ConfigParser
import serial
import subprocess
import logging
import datetime
from twilio.rest import Client
import urllib2
import json
import httplib
from subprocess import call
import requests
from utilities import get_ph
from utilities import get_orp

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
# a three wire connection with ground and 5V plus GPIO for detecting the
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

# Setup to read and write to a status file:
def read_pool_sensor_status_values(file, section, status):
    pathname = '/var/www/' + file
    config.read(pathname)
    current_status = config.get(section, status)
    return current_status

def update_pool_sensor_status_values(file, section, status, value):
    pathname = '/var/www/' + file
    config.read(pathname)
    cfgfile = open(pathname, 'w')
    config.set(section, status, value)
    config.write(cfgfile)
    cfgfile.close()


#########################################
# Set up Logging & Notifications
#########################################
DEBUG = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug")
LOGGING = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "logging")
EMAIL = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "email")
PUSHBULLET = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "pushbullet")
SMS = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms")

alert_email = pooldb.alert_email


if LOGGING == "True":
    logger = logging.getLogger(__name__)
    handler = logging.FileHandler('/var/log/pool_control_master.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.filemode = 'a'


# Setup to send email via the builtin linux mail command. Your local system should be configured already to send mail.
def send_email(recipient, subject, body):
    process = subprocess.Popen(['mail', '-s', subject, recipient],stdin=subprocess.PIPE)
    process.communicate(body)

# Setup to send out Pushbillet alerts if configured above
def send_push_notification(title, message):
    pb = Pushbullet(pooldb.pushbilletAPI)
    push = pb.push_note(title, message)

# Setup to send SMS Text messages via Twilio if configured above
def send_sms_notification(body):
    client = Client(pooldb.twilio_account, pooldb.twilio_token)
    message = client.messages.create(to=pooldb.twilio_to, from_=pooldb.twilio_from,
                                         body=body)

def mightyhat_serial_setup():
    #TODO Finish setting up MightyHat message management
    """ Setup Serial communication with Mightyhat LCD screen. """
    global ser
    ser = serial.Serial(
        port='/dev/ttyAMA0',
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1)
    if DEBUG == "True":
        print("MightyHat Serial setup completed")

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


# Convert Pool Resistance reading to Percentage for web interface
def get_pool_level_percentage(level):
    global pool_level_percentage
    if level <= 710:
        pool_level_percentage = 100
    elif level == 711:
        pool_level_percentage = 99
    elif level == 712:
        pool_level_percentage = 97
    elif level == 713:
        pool_level_percentage = 96
    elif level == 714:
        pool_level_percentage = 95
    elif level == 715:
        pool_level_percentage = 94
    elif level == 716:
        pool_level_percentage = 93
    elif level == 717:
        pool_level_percentage = 92
    elif level == 718:
        pool_level_percentage = 91
    elif level == 719:
        pool_level_percentage = 90
    elif level == 720:
        pool_level_percentage = 89
    elif level == 721:
        pool_level_percentage = 88
    elif level == 722:
        pool_level_percentage = 87
    elif level == 723:
        pool_level_percentage = 86
    elif level == 724:
        pool_level_percentage = 85
    elif level == 725:
        pool_level_percentage = 84
    elif level == 726:
        pool_level_percentage = 83
    elif level == 727:
        pool_level_percentage = 82
    elif level == 728:
        pool_level_percentage = 81
    elif level == 729:
        pool_level_percentage = 80
    elif level == 730:
        pool_level_percentage = 79
    elif level == 731:
        pool_level_percentage = 78
    elif level == 732:
        pool_level_percentage = 77
    elif level == 733:
        pool_level_percentage = 76
    elif level == 734:
        pool_level_percentage = 75
    elif level == 735:
        pool_level_percentage = 74
    elif level == 736:
        pool_level_percentage = 73
    elif level == 737:
        pool_level_percentage = 72
    elif level == 738:
        pool_level_percentage = 71
    elif level == 739:
        pool_level_percentage = 70
    else:
        pool_level_percentage = 69
    return pool_level_percentage



# Convert our battery voltages to percentages for web interface
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



# is our pump control system active and responding?
def check_pump_control_url():
    check_url = pooldb.PUMP_DATA_TEST_URL
    conn = httplib.HTTPConnection(check_url, timeout=3)
    try:
        conn.request("HEAD", "/")
        conn.close()
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active", True)
        return True
    except:
        conn.close()
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active", False)
        return False


# Function to talk to pump control software
# See https://github.com/tagyoureit/nodejs-poolController
def get_pump_data(key):
    global json
    global pump_data
    req = urllib2.Request(pooldb.PUMP_DATA_URL)
    opener = urllib2.build_opener()
    f = opener.open(req)
    json = json.loads(f.read())
    pump_data = json["pump"]["1"][key]
    return pump_data

# This funtcion is only called externally by our Flask template
def pump_control(command):
    pump_control_active = check_pump_control_url()
    DEBUG = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug")
    LOGGING = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "logging")
    EMAIL = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "email")
    PUSHBULLET = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "pushbullet")
    SMS = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms")
    pump_program_running = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running")
    pump_control_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_notifications")
    if pump_control_active:
        if command == "START":
            urllib2.urlopen(pooldb.PUMP_START_URL)
            update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
            if DEBUG == "True":
                print("pump_control() called with START command")
            if LOGGING == "True":
                logger.warn("pump_control() called with START command.")
            if EMAIL == "True" and  pump_control_notifications == "True":
                send_email(pooldb.alert_email, 'Your pool pump has been Started', 'Your pool pump has been started.')
            if PUSHBULLET == "True" and  pump_control_notifications == "True":
                send_push_notification("Your pool pump has been started.", "Your pool pump has been started.")
            if SMS == "True" and  pump_control_notifications == "True":
                send_sms_notification("Your pool pump has been started.")
        elif command == "PROGRAM_1":
            if pump_program_running == "program_1":
                pass
            else:
                urllib2.urlopen(pooldb.PUMP_PROGRAM1_URL)
                update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                if DEBUG == "True":
                    print("pump_control() called with PROGRAM 1 command")
                if LOGGING == "True":
                    logger.warn("pump_control() called with PROGRAM 1 command.")
                if EMAIL == "True" and  pump_control_notifications == "True":
                    send_email(pooldb.alert_email, 'Your pool pump has started Program 1', 'Your pool pump has started Program 1.')
                if PUSHBULLET == "True" and  pump_control_notifications == "True":
                    send_push_notification("Pool Pump Program 1.", "Your pool pump has started Program 1.")
                if SMS == "True" and  pump_control_notifications == "True":
                    send_sms_notification("Your pool pump has started Program 1.")
        elif command == "PROGRAM_2":
            if pump_program_running == "program_2":
                pass
            else:
                urllib2.urlopen(pooldb.PUMP_PROGRAM2_URL)
                update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                if DEBUG == "True":
                    print("pump_control() called with PROGRAM 2 command")
                if LOGGING == "True":
                    logger.warn("pump_control() called with PROGRAM 2 command.")
                if EMAIL == "True" and  pump_control_notifications == "True":
                    send_email(pooldb.alert_email, 'Your pool pump has started Program 2', 'Your pool pump has started Program 2.')
                if PUSHBULLET == "True" and  pump_control_notifications == "True":
                    send_push_notification("Pool Pump Program 2.", "Your pool pump has started Program 2.")
                if SMS == "True" and  pump_control_notifications == "True":
                    send_sms_notification("Your pool pump has started Program 2.")
        elif command == "PROGRAM_3":
            if pump_program_running == "program_3":
                pass
            else:
                urllib2.urlopen(pooldb.PUMP_PROGRAM3_URL)
                update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                if DEBUG == "True":
                    print("pump_control() called with PROGRAM 3 command")
                if LOGGING == "True":
                    logger.warn("pump_control() called with PROGRAM 3 command.")
                if EMAIL == "True" and  pump_control_notifications == "True":
                    send_email(pooldb.alert_email, 'Your pool pump has started Program 3', 'Your pool pump has started Program 3.')
                if PUSHBULLET == "True" and  pump_control_notifications == "True":
                    send_push_notification("Pool Pump Program 3.", "Your pool pump has started Program 3.")
                if SMS == "True" and  pump_control_notifications == "True":
                    send_sms_notification("Your pool pump has started Program 3.")
        elif command == "PROGRAM_4":
            if pump_program_running == "program_4":
                pass
            else:
                urllib2.urlopen(pooldb.PUMP_PROGRAM4_URL)
                update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
                if DEBUG == "True":
                    print("pump_control() called with PROGRAM 4 command")
                if LOGGING == "True":
                    logger.warn("pump_control() called with PROGRAM 4 command.")
                if EMAIL == "True" and  pump_control_notifications == "True":
                    send_email(pooldb.alert_email, 'Your pool pump has started Program 4', 'Your pool pump has started Program 4.')
                if PUSHBULLET == "True" and  pump_control_notifications == "True":
                    send_push_notification("Pool Pump Program 4.", "Your pool pump has started Program 4.")
                if SMS == "True" and  pump_control_notifications == "True":
                    send_sms_notification("Your pool pump has started Program 4.")
        else:
            urllib2.urlopen(pooldb.PUMP_STOP_URL)
            update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", False)
            if DEBUG == "True":
                print("pump_control() called with STOP command")
            if LOGGING == "True":
                logger.warn("pump_control() called with STOP command.")
            if EMAIL == "True" and  pump_control_notifications == "True":
                send_email(pooldb.alert_email, 'Your pool pump has been stopped', 'Your pool pump has been stopped.')
            if PUSHBULLET == "True" and  pump_control_notifications == "True":
                send_push_notification("Your pool pump has been stopped.", "Your pool pump has been stopped.")
            if SMS == "True" and  pump_control_notifications == "True":
                send_sms_notification("Your pool pump has been stopped.")
    else:
        pass


def get_pump_gpm():
    pump_control_active = check_pump_control_url()
    if pump_control_active:
        if pooldb.PUMP_DATA == "NODEJS":
            global gpm 
            global pump_gpm
            req = urllib2.Request(pooldb.PUMP_DATA_URL)
            opener = urllib2.build_opener()
            g = opener.open(req)
            gpm = json.loads(g.read())
            pump_gpm = gpm["pump"]["1"]["gpm"]
            update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_gpm", pump_gpm)
            return pump_gpm
        else:
            pump_gpm = 0
            update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_gpm", pump_gpm)
            return pump_gpm
    else:
        pump_gpm = 0
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_gpm", pump_gpm)
        return pump_gpm

def get_pump_rpm():
    pump_control_active = check_pump_control_url()
    if pump_control_active:
        if pooldb.PUMP_DATA == "NODEJS":
            global rpm 
            global pump_rpm
            req = urllib2.Request(pooldb.PUMP_DATA_URL)
            opener = urllib2.build_opener()
            f = opener.open(req)
            rpm = json.loads(f.read())
            pump_rpm = rpm["pump"]["1"]["rpm"]
            update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_rpm", pump_rpm)
            return pump_rpm
        else:
            pump_rpm = 0
            update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_rpm", pump_rpm)
            return pump_rpm
    else:
        pump_rpm = 0
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_rpm", pump_rpm)
        return pump_rpm


def get_pump_watts():
    global watts 
    global pump_watts
    req = urllib2.Request(pooldb.PUMP_DATA_URL)
    opener = urllib2.build_opener()
    f = opener.open(req)
    watts = json.loads(f.read())
    pump_watts = watts["pump"]["1"]["watts"]
    return pump_watts


def pump_control_software(startstop):
    DEBUG = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug")
    LOGGING = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "logging")
    EMAIL = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "email")
    PUSHBULLET = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "pushbullet")
    SMS = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms")
    pump_control_software_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_software_notifications")
    if startstop == "START":
        call(["pm2", "start", "index"])
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active", True)
        if DEBUG == "True":
            print("pump_control_software() called with START command")
        if LOGGING == "True":
            logger.warn("pump_control_software() called with START command.")
        if EMAIL == "True" and pump_control_software_notifications == "True":
            send_email(pooldb.alert_email, 'Your Pump Control Software is Active', 'Your pump control software is active.')
        if PUSHBULLET == "True" and pump_control_software_notifications == "True":
            send_push_notification("Your pump control software is active.", "Your pump control software has been started.")
        if SMS == "True" and pump_control_software_notifications == "True":
            send_sms_notification("Your pump control software is active.")
    else:
        call(["pm2", "stop", "index"])
        update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active", False)
        if DEBUG == "True":
            print("pump_control_software() called with STOP command")
        if LOGGING == "True":
            logger.warn("pump_control_software() called with STOP command.")
        if EMAIL == "True" and pump_control_software_notifications == "True":
            send_email(pooldb.alert_email, 'Your Pump Control Software has been disabled.', 'Your pump control software has been disabled.')
        if PUSHBULLET == "True" and pump_control_software_notifications == "True":
            send_push_notification("Your pump control software has been disabled.", "Your pump control software has been disabled.")
        if SMS == "True" and pump_control_software_notifications == "True":
            send_sms_notification("Your pump control software has been disabled.")


def get_sprinkler_status():
    """ Function to determine if our sprinklers are currently running. """
    if DEBUG == "True":
        print("Started get_sprinkler_status().")
    if pooldb.sprinkler_type == "Timer":
        SprinklerStart = int(400)
        SprinklerStop = int(1000)

        current_military_time = int(datetime.datetime.now().strftime('%H%M'))

        if SprinklerStart < current_military_time < SprinklerStop:
            sprinklers_on = "True"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", True)
            if DEBUG == "True":
                print("Sprinklers running (TIMER)")
            led_control(sprinkler_run_led, "True")
            if DEBUG == "True":
                print("SPRINKLER_RUN_LED should be ON. This is a BLUE LED")
        else:
            sprinklers_on = "False"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", False)
            if DEBUG == "True":
                print("Sprinklers are not running (TIMER)")
            led_control(sprinkler_run_led, "False")
            if DEBUG == "True":
                print("SPRINKLER_RUN_LED should be OFF. This is a BLUE LED")
        return sprinklers_on
    else:
        if DEBUG == "True":
            print("subprocess call for sprinklers called.")
        output = subprocess.check_output(pooldb.rachio_url, shell=True)
        if output == "{}":
            sprinklers_on = "False"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", False)
            if DEBUG == "True":
                print("Sprinklers are not running (RACHIO).")
            led_control(sprinkler_run_led, "False")
            if DEBUG == "True":
                print("SPRINKLER_RUN_LED should be OFF. This is a BLUE LED")
        else:
            sprinklers_on = "True"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", True)
            if DEBUG == "True":
                print("Sprinklers running. (RACHIO)")
            led_control(sprinkler_run_led, "True")
            if DEBUG == "True":
                print("SPRINKLER_RUN_LED should be ON. This is a BLUE LED")
    if DEBUG == "True":
        print("Completed get_sprinkler_status()")
    return sprinklers_on


## Here is where we get our pH reading if we have a probe installed.
## In order to get an accurate pH reading the way the sensors are
## installed, we must have the pool pump running. Here is where we
## check to see if the pool pump is running. If it is, we get the
## pH reading, if it is not, we do nothing but log the fact the pump
## is not running.

def get_ph_reading():
    pool_pump_running = read_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led" )
    if pool_pump_running == "True":
        if DEBUG == "True":
            print("Starting get_ph_reading().")
        if pooldb.temp_probe == "Yes":
            pool_temp = float(read_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_current_temp" ))
            ph_value = get_ph.get_current_ph_with_temp(pool_temp)
        else:
            ph_value = get_ph.get_current_ph_no_temp()
        if DEBUG == "True":
            print ("Current pH is: %s" % ph_value)
        if pooldb.emoncms_server1 == "Yes":
            res = requests.get("http://" + pooldb.server1 + "/" + pooldb.emoncmspath1 + "/input/post.json?&node=" + str(
                pooldb.ph_node) + "&csv=" + ph_value + "&apikey=" + pooldb.apikey1)
            if LOGGING == "True":
                logger.debug("Sent current PH Value: %s to Emoncms Server 1",  ph_value)
            if DEBUG == "True":
                print ("Sent Emoncms Server 1 current PH Value: %s" % ph_value)
        if pooldb.emoncms_server2 == "Yes":
            res = requests.get("http://" + pooldb.server2 + "/" + pooldb.emoncmspath2 + "/input/post.json?&node=" + str(
                pooldb.ph_node) + "&csv=" + ph_value + "&apikey=" + pooldb.apikey2)
            if LOGGING == "True":
                logger.debug("Sent current PH Value: %s to Emoncms Server 2", ph_value)
            if DEBUG == "True":
                print ("Sent Emoncms Server 2 current PH Value: %s" % ph_value)
        update_pool_sensor_status_values("pool_sensor_status", "pool_chemicals", "pool_current_ph", ph_value)
        if DEBUG == "True":
            print("Completed get_ph_reading()")
    else:
        if LOGGING == "True":
            logger.info("Pool Pump is NOT running, cannot get accurate pH reading!")
        if DEBUG == "True":
            print("Pool pump is NOT running, cannot get accurate pH reading!")



## If we have an ORP Probe installed (Atlas Scientific USB) set it up here.
## In order to get an accurate ORP reading the way the sensors are
## installed, we must have the pool pump running. Here is where we
## check to see if the pool pump is running. If it is, we get the
## ORP reading, if it is not, we do nothing but log the fact the pump
## is not running.

def get_orp_reading():
    pool_pump_running = read_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led" )
    if pool_pump_running == "True":
        if DEBUG == "True":
            print("Starting get_orp_reading().")
        orp_value = get_orp.get_current_orp()
        if pooldb.emoncms_server1 == "Yes":
            res = requests.get("http://" + pooldb.server1 + "/" + pooldb.emoncmspath1 + "/input/post.json?&node=" + str(
                pooldb.orp_node) + "&csv=" + orp_value + "&apikey=" + pooldb.apikey1)
            if LOGGING == "True":
                logger.debug("Sent current ORP Value: %s to Emoncms Server 1", orp_value)
            if DEBUG == "True":
                print ("Sent Emoncms Server 1 current ORP Value: %s" % orp_value)
        if pooldb.emoncms_server2 == "Yes":
            res = requests.get("http://" + pooldb.server2 + "/" + pooldb.emoncmspath2 + "/input/post.json?&node=" + str(
                pooldb.orp_node) + "&csv=" + orp_value + "&apikey=" + pooldb.apikey2)
            if LOGGING == "True":
                logger.debug("Sent current ORP Value: %s to Emoncms Server 2", orp_value)
            if DEBUG == "True":
                print ("Sent Emoncms Server 2 current ORP Value: %s" % orp_value)
        
        update_pool_sensor_status_values("pool_sensor_status", "pool_chemicals", "pool_current_orp", orp_value)
        if DEBUG == "True":
            print("Completed get_orp_reading()")
    else:
        if LOGGING == "True":
            logger.info("Pool Pump is NOT running, cannot get accurate ORP reading!")
        if DEBUG == "True":
            print("Pool pump is NOT running, cannot get accurate ORP reading!")




# TODO - Complete this function, add notification via PB once until PFV reenabled!
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
    DEBUG = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug")
    LOGGING = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "logging")
    EMAIL = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "email")
    PUSHBULLET = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "pushbullet")
    SMS = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms")
    pool_fill_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_notifications")
    current_timestamp = int(time.time())
    if openclose == "OPEN":
       sprinkler_status = get_sprinkler_status()
       if sprinkler_status == "True":
           if DEBUG == "True":
               print("Sprinklers are running, we cannot fill the pool at this time, we will try again later.")
           if LOGGING == "True":
               logger.info("Sprinklers are running, we cannot fill the pool at this time, we will try again later.")
           pass
       pool_level_sensor_ok = read_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok")
       if pool_level_sensor_ok == "False":
           if DEBUG == "True":
               print("There is a problem with your pool level sensor and we cannot fill the pool.")
           if LOGGING == "True":
               logger.warn("There is a problem with your pool level sensor and we cannot fill the pool.")
           if EMAIL == "True" and pool_fill_notifications == "True":
               send_email(pooldb.alert_email, 'Problem with your Pool Level Sensor', 'There is a problem with your Pool Level Sensor and we cannot refill the pool!')
           if PUSHBULLET == "True" and pool_fill_notifications == "True":
               send_push_notification("There is a problem with your Pool Level Sensor", "Pool Level Sesnor Error - We cannot refill your pool!")
           if SMS == "True" and pool_fill_notifications == "True":
               send_sms_notification("There is a problem with your Pool Level Sensor and we cannot refill your pool!")
           pass
       gallons_start = get_gallons_total()
       update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_start", gallons_start)
       update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", True)
       update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time", current_timestamp)
       GPIO.output(pool_fill_transformer_relay, True)  # Turns on the Sprinkler Transformer
       GPIO.output(pool_fill_relay, True)  # Turns on the sprinkler valve
       led_control(pool_filling_led, "True") # Turns on the pool filling blue LED
       update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", True)
       if LOGGING == "True":
           logger.info("Pool is low and is automatically refilling.")
       if DEBUG == "True":
           print("pool_fill_valve called with OPEN command")
           print("pool_fill_transformer_relay is now powered and pool transformer is now ACTIVE")
           print("pool_fill_relay is now powered and sprinkler valve solenoid is now powered.")
           print("Both relays should now be active and Sprinkler valve should be open and water should be running.")
           print("Pool Filling LED should be on. This is a BLUE LED")
       if PUSHBULLET == "True" and pool_fill_notifications == "True":
           send_push_notification("Your Pool Is Automatically Filling", "Your swimming pool is low and is automatically refilling.")
       if SMS == "True" and pool_fill_notifications == "True":
           send_sms_notification("Your Swimming Pool Is Automatically Filling")
       if EMAIL == "True" and pool_fill_notifications == "True":
           send_email(pooldb.alert_email, 'Your Pool is Automatically Filling', 'Your Pool is low and is automatically refilling.')
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
        if LOGGING == "True":
            logger.info("Pool is done refilling.")
        if DEBUG == "True":
            print("pool_fill_valve called with CLOSE command")
            print("pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered.")
            print("pool_fill_transformer_relay is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")
        if PUSHBULLET == "True" and pool_fill_notifications == "True":
            send_push_notification("Your Pool is Done Automatically Filling", "Your swimming pool is done refilling.")
        if SMS == "True" and pool_fill_notifications == "True":
            send_sms_notification("Your Pool is Done Automatically Filling")
        if EMAIL == "True" and pool_fill_notifications == "True":
            send_email(pooldb.alert_email, 'Your Pool is Done Automatically Filling', 'Your pool is done refilling!')
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
        if LOGGING == "True":
            logger.info("Auto Fill terminated by Web Request.")
        if DEBUG == "True":
            print("pool_fill_valve called with WEBCLOSE command")
            print("pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered.")
            print("pool_fill_transformer_relay is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")
        if PUSHBULLET == "True" and pool_fill_notifications == "True":
            send_push_notification("Pool Auto Fill terminated by Web Request", "Your swimming pool has stopped filling due to a Web request.")
        if SMS == "True" and pool_fill_notifications == "True":
            send_sms_notification("Pool Auto Fill terminated by Web Request")
        if EMAIL == "True" and pool_fill_notifications == "True":
            send_email(pooldb.alert_email, 'Pool Auto Fill Terminated by Web Request', 'Your swimming pool has stopped filling due to a web request')
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
        if LOGGING == "True":
            logger.warn("Pool Fill CRITICAL Stop!")
        if DEBUG == "True":
            print("pool_fill_valve called with CRITICAL CLOSE command")
            print("pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered.")
            print("Pool filling LED should be off. This is a BLUE LED.")
            print("System Error LED should be on. This is a RED LED.")
            print("pool_fill_transformer_relay is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")
        if PUSHBULLET == "True" and pool_fill_notifications == "True":
            send_push_notification("Pool Fill Stopped with CRITICAL CLOSE", "Your swimming pool fill was stopped by a CRITICAL CLOSE Command.")
        if SMS == "True" and pool_fill_notifications == "True":
            send_sms_notification("Pool Fill Stopped with CRITICAL CLOSE! Check Your System!")
        if EMAIL == "True" and pool_fill_notifications == "True":
            send_email(pooldb.alert_email, 'Pool Fill - CRITICAL STOP!', 'You pool has stopped filling due to a CRITICAL STOP! Please check the system.')
    elif openclose == "RESET":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        gallons_stop = get_gallons_total()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_stop", gallons_stop)
        calculate_gallons_used()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", 0)
        if DEBUG == "True":
            print("pool_fill_valve called with RESET command")
        if LOGGING == "True":
            logger.info("pool_fill_valve called with RESET command")
    elif openclose == "MANUAL_OPEN":
        sprinkler_status = get_sprinkler_status()
        if sprinkler_status == "True":
            blink_led(manual_fill_button_led, 7, 0.1)
            if DEBUG == "True":
                print("Sprinklers are running, we cannot fill the pool at this time, we will try again later.")
            pass
        pool_level_sensor_ok = read_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok")
        if pool_level_sensor_ok == "False":
            blink_led(manual_fill_button_led, 7, 0.1)
            if DEBUG == "True":
                print("There is a problem with your pool level sensor and we cannot fill the pool.")
            pass
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", True)
        gallons_start = get_gallons_total()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_start", gallons_start)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time", current_timestamp)
        GPIO.output(pool_fill_transformer_relay, True)  # Turns on the Sprinkler Transformer
        GPIO.output(pool_fill_relay, True)  # Turns on the sprinkler valve
        led_control(pool_filling_led, "True")  # Turns on the pool filling blue LED
        led_control(manual_fill_button_led, "True")
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", True)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "manual_fill_button_led", True)
        if PUSHBULLET == "True" and pool_fill_notifications == "True":
            send_push_notification("Your Pool is MANUALLY Filling", "Your swimming pool is MANUALLY refilling.")
        if SMS == "True" and pool_fill_notifications == "True":
            send_sms_notification("Your Swimming Pool is MANUALLY Filling")
        if LOGGING == "True":
            logger.info("Your Pool is MANUALLY Filling.")
        if EMAIL == "True" and pool_fill_notifications == "True":
            send_email(pooldb.alert_email, 'Your pool is MANUALLY Filling', 'Your pool is being manually filled!')
        if DEBUG == "True":
            print("MANUAL FILL BUTTON - pool_fill_valve called with OPEN command")
            print("pool_fill_transformer_relay is now powered and pool transformer is now ACTIVE")
            print("pool_fill_relay is now powered and sprinkler valve solenoid is now powered.")
            print("Both relays should now be active and Sprinkler valve should be open and water should be running.")
            print("Pool Filling LED should be on. This is a BLUE LED")
    elif openclose == "MANUAL_CLOSE":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(manual_fill_button_led, "False")
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        gallons_stop = get_gallons_total()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_stop", gallons_stop)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "manual_fill_button_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        calculate_gallons_used()
        update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", 0)
        if LOGGING == "True":
            logger.info("Your Pool is done MANUALLY Filling.")
        if DEBUG == "True":
            print("MANUAL FILL BUTTON - pool_fill_valve called with CLOSE command")
            print("pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered.")
            print("pool_fill_transformer_relay is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")
        if PUSHBULLET == "True" and pool_fill_notifications == "True":
            send_push_notification("Your Pool Is Done (MANUALLY) Filling", "Your swimming pool is done (MANUALLY) refilling.")
        if SMS == "True" and pool_fill_notifications == "True":
            send_sms_notification("Your Swimming Pool Is Done (MANUALLY) Filling.")
        if EMAIL == "True" and pool_fill_notifications == "True":
            send_email(pooldb.alert_email, 'Your Pool is done MANUALLY Filling.', 'Your Pool is done MANUALLY Filling.')


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
        if DEBUG == "True":
            print("Total Current Power Utilization: %s watts" % power_total_use)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.power_importing))

    for data in cursor:
        power_importing = int("%1.0f" % data)
        cursor.close()
        update_pool_sensor_status_values("pool_sensor_status", "power_solar", "total_current_power_import", power_importing)
        if DEBUG == "True":
            print("Total Current Power Import: %s watts" % power_importing)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.power_solar))

    for data in cursor:
        power_solar = int("%1.0f" % data)
        cursor.close()
        update_pool_sensor_status_values("pool_sensor_status", "power_solar", "total_current_solar_production", power_solar)
        if DEBUG == "True":
            print("Total Current Solar Production: %s watts" % power_solar)

    cnx.close()





# Track total gallons added to pool during fill times
def get_gallons_total():
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
        if DEBUG == "True":
            print("Total Gallons: %s" % pool_gallons_total)

    cnx.close()
    return pool_gallons_total

def calculate_current_fill_gallons():
    fill_gallons_start = get_gallons_total()
    fill_gallons_stop = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons","gallons_stop")
    current_fill_gallons = int(fill_gallons_start) - int(fill_gallons_stop)
    update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill", current_fill_gallons)
    return current_fill_gallons

def calculate_gallons_used():
    gallons_start = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons","gallons_start") 
    gallons_stop = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons","gallons_stop") 
    gallons_used = int(gallons_stop) - int(gallons_start)
    update_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_last_fill", gallons_used) 

def check_pool_sensors():
    if DEBUG == "True":
        print ("Current unix datetime stamp is: %s" % current_timestamp)
    
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
        if DEBUG == "True":
            print("Pool LEVEL sensor last updated at: %s" % get_pool_level_sensor_time)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_level_sensor_battery_table))

    for data in cursor:
        get_pool_level_sensor_battery_voltage = float("%1.2f" % data)
        cursor.close()
        get_battery_percentage(get_pool_level_sensor_battery_voltage)
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_level_batt_percentage", batt_level)
        if DEBUG == "True":
            print("Pool LEVEL sensor battery voltage is: %s" % get_pool_level_sensor_battery_voltage)
            print ("Pool LEVEL sensor battery percentage  is %s" % batt_level)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT time FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_temp_table))

    for data in cursor:
        get_pool_temp_sensor_time = int("%1.0f" % data)
        cursor.close()
        if DEBUG == "True":
            print("Pool TEMP sensor last updated at: %s" % get_pool_temp_sensor_time)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_temp_sensor_battery_table))

    for data in cursor:
        get_pool_temp_sensor_battery_voltage = float("%1.2f" % data)
        cursor.close()
        get_battery_percentage(get_pool_temp_sensor_battery_voltage)
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_temp_batt_percentage", batt_level)
        if DEBUG == "True":
            print("Pool TEMP sensor battery voltage is: %s" % get_pool_temp_sensor_battery_voltage)
            print ("Pool TEMP sensor battery percentage  is %s" % batt_level)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pool_filter_psi_table))
    for data in cursor:
        get_pool_filter_psi = int("%1.0f" % data)
        cursor.close()
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "filter_current_psi", get_pool_filter_psi)
        if DEBUG == "True":
            print("Pool FILTER PSI is: %s" % get_pool_filter_psi)

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

    if DEBUG == "True":
        print ("Time dfference between last pool LEVEL sensor reading is: %s "
            "seconds." % pool_level_sensor_time_delta)
        print ("Time dfference between last pool TEMP sensor reading is: %s "
            "seconds." % pool_temp_sensor_time_delta)

    if pool_level_sensor_time_delta > pooldb.max_pool_level_sensor_time_delta:
        if pool_level_timeout_alert_sent == "True":
            pass
        else:
            if PUSHBULLET == "True" and pool_level_sensor_notifications == "True":
                send_push_notification("Pool Level Sensor Timeout", "Your Pool Level Sensor has Timed Out!")
            if SMS == "True" and pool_level_sensor_notifications == "True":
                send_sms_notification("Your Pool Level Sensor has Timed Out!")
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", False)
            if LOGGING == "True":
                logger.warn("Pool LEVEL sensor timeout!")
            if EMAIL == "True" and pool_level_sensor_notifications == "True":
                send_email(pooldb.alert_email, 'Pool LEVEL sensor timeout.', 'Your Pool Level sensor has timed out.')
        if DEBUG == "True":
            print ("* * * * WARNING * * * *")
            print ("Pool LEVEL Sensor Timeout!")
    elif pool_level_sensor_time_delta < pooldb.max_pool_level_sensor_time_delta and pool_level_timeout_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", True)
        if PUSHBULLET == "True" and pool_level_sensor_notifications == "True":
            send_push_notification("Pool Level Sensor Timeout Has Ended", "Your Pool Level Sensor is Back Online!")
        if SMS == "True" and pool_level_sensor_notifications == "True":
            send_sms_notification("Your Pool Level Sensor is Back Online!")
        if LOGGING == "True":
            logger.info("Pool LEVEL sensor timeout has ended! Pool level sensor back online.")
        if EMAIL == "True" and pool_level_sensor_notifications == "True":
            send_email(pooldb.alert_email, 'Pool LEVEL sensor back Online.', 'Your Pool Level sensor is back Online.')

    elif get_pool_level_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
        if pool_level_lowvoltage_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", False)
            if PUSHBULLET == "True" and pool_level_sensor_notifications == "True":
                send_push_notification("Pool Level Sensor Low Voltage", "The battery is low in your pool level sensor.")
            if SMS == "True" and pool_level_sensor_notifications == "True":
                send_sms_notification("The battery is low in your pool level sensor.")
            if LOGGING == "True":
                logger.warn("Pool LEVEL sensor Low Voltage!")
            if EMAIL == "True" and pool_level_sensor_notifications == "True":
                send_email(pooldb.alert_email, 'Pool LEVEL sensor LOW VOLTAGE.', 'Please replace the Pool LEVEL sensor batteries.')
        if DEBUG == "True":
            print ("* * * * WARNING * * * *")
            print ("Pool LEVEL Sensor Battery Voltage LOW!")
    elif get_pool_level_sensor_battery_voltage > pooldb.pool_level_sensor_low_voltage and pool_level_lowvoltage_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", True)
        if LOGGING == "True":
            logger.info("Pool LEVEL Sensor Battery level is Normal")

    elif pool_temp_sensor_time_delta > pooldb.max_pool_temp_sensor_time_delta:
        if pool_temp_timeout_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent", True)
            if PUSHBULLET == "True" and pool_temp_sensor_notifications == "True":
                send_push_notification("Pool Temp Sensor Timeout", "Your Pool Temp Sensor has Timed Out!")
            if SMS == "True" and pool_temp_sensor_notifications == "True":
                send_sms_notification("Your Pool Temp Sensor has Timed Out!")
            if LOGGING == "True":
                logger.warn("Pool TEMP sensor timeout!")
            if EMAIL == "True" and pool_temp_sensor_notifications == "True":
                send_email(pooldb.alert_email, 'Pool Temp sensor TIME OUT.', 'Your Pool temperature sensor has timed out.')
        if DEBUG == "True":
            print ("* * * * WARNING * * * *")
            print ("Pool TEMP Sensor Timeout!")
    elif pool_temp_sensor_time_delta < pooldb.max_pool_temp_sensor_time_delta and pool_temp_timeout_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent", False)
        if PUSHBULLET == "True" and pool_temp_sensor_notifications == "True":
            send_push_notification("Pool Temp Sensor Timeout Has Ended", "Your Pool Temp Sensor is Back Online!")
        if SMS == "True" and pool_temp_sensor_notifications == "True":
            send_sms_notification("Your Pool Temp Sensor is Back Online!")
        if LOGGING == "True":
            logger.info("Pool TEMP Sensor is back online")
        if EMAIL == "True" and pool_temp_sensor_notifications == "True":
            send_email(pooldb.alert_email, 'Pool TEMP sensor back Online.', 'Your Pool Temperature sensor is back Online.')

    elif get_pool_temp_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
        if pool_temp_lowvoltage_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_low_voltage_alert_sent", True)
            if PUSHBULLET == "True" and pool_temp_sensor_notifications == "True":
                send_push_notification("Pool Temp Sensor Low Voltage", "The battery is low in your pool temp sensor.")
            if SMS == "True" and pool_temp_sensor_notifications == "True":
                send_sms_notification("The battery is low in your pool temp sensor.")
            if LOGGING == "True":
                logger.warn("Pool TEMP sensor Low Voltage!")
            if EMAIL == "True" and pool_temp_sensor_notifications == "True":
                send_email(pooldb.alert_email, 'Pool TEMP sensor LOW VOLTAGE.', 'Please replace the Pool floating TEMP sensor batteries.')
        if DEBUG == "True":
            print ("* * * * WARNING * * * *")
            print ("Pool TEMP Sensor Battery Voltage LOW!")
    elif get_pool_temp_sensor_battery_voltage > pooldb.pool_level_sensor_low_voltage and pool_temp_lowvoltage_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_low_voltage_alert_sent", False)
        if LOGGING == "True":
            logger.info("Pool TEMP Sensor Battery level is Normal")

    elif get_pool_filter_psi > pooldb.pool_filter_max_psi:
        if pool_filter_psi_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_filter_psi_alert_sent", True)
            if PUSHBULLET == "True" and pool_filter_psi_notifications == "True":
                send_push_notification("Pool Filter HIGH PSI", "It is time to BACK FLUSH your pool filter")
            if SMS == "True" and pool_filter_psi_notifications == "True":
                send_sms_notification("Pool Filter HIGH PSI - It is time to BACK FLUSH your pool filter")
            if EMAIL == "True" and pool_filter_psi_notifications == "True":
                send_email(pooldb.alert_email, 'Pool Filter HIGH PSI', 'Your Pool Filter needs to be backflushed or checked!')
            if LOGGING == "True":
                logger.warn("Pool filter PSI is HIGH!")
        if DEBUG == "True":
            print ("* * * * WARNING * * * *")
            print ("Pool Filter Pressure HIGH - Backflush your filter!")
    elif get_pool_filter_psi < pooldb.pool_filter_max_psi_reset and pool_filter_psi_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_filter_psi_alert_sent", False)
        if LOGGING == "True":
            logger.info("Pool filter PSI is Normal")

    else:
        if DEBUG == "True":
            print ("Everything appears to be OK with the pool sensors!")


def get_pool_level_resistance():
    pool_manual_fill = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill")
    pool_fill_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_notifications")
    if pool_manual_fill == "True":
        current_timestamp = int(time.time())
        if DEBUG == "True":
            print("Pool is Manually Filling - Automatic Fill disabled!")
        pool_fill_start_time = int(read_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time"))
        pool_fill_total_time = (current_timestamp - pool_fill_start_time) / 60
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", pool_fill_total_time)
        current_fill_gallons = calculate_current_fill_gallons()
        if DEBUG == "True":
            print ("Pool has been MANUALLY filling for %s minutes." % pool_fill_total_time)
            print ("Current gallons of water added to pool: %s gallons." % current_fill_gallons)
        if pool_fill_total_time >= pooldb.max_pool_fill_time:
            update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
            if PUSHBULLET == "True" and pool_fill_notifications == "True":
                send_push_notification("Pool MANUAL Fill Critical Stop", "Your Pool has been MANUALLY filling too long. Critical Stop. Check System!")
            if SMS == "True" and pool_fill_notifications == "True":
                send_sms_notification("Pool MANUAL Fill Critical Stop - Your Pool has been MANUALLY filling too long. Critical Stop. Check System!")
            if EMAIL == "True" and pool_fill_notifications == "True":
               send_email(pooldb.alert_email, 'Pool MANUAL Fill Critical Stop', 'Your Pool has been manually filling too long. Critical Stop. Check System!')
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
            pool_fill_valve("CRITICALCLOSE")
            update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", False)
            if DEBUG == "True":
                print("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
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
            if DEBUG == "True":
                print("pool_sensors: Pool Resistance is: %s " % get_pool_level_resistance_value)
                print("pool_sensors: Pool Level Percentage is: %s " % pool_level_percentage)
                print("pooldb: Static critical pool level resistance set at ("
                    "%s)." % pooldb.pool_resistance_critical_level)
                print("pooldb: Static normal pool level resistance set at (%s)." %
                    pooldb.pool_resistance_ok_level)
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
                if DEBUG == "True":
                    print ("Pool has been filling for %s minutes." % pool_fill_total_time)
                    print ("Current number of gallons added to pool: %s gallons." % current_fill_gallons)
                if pool_fill_total_time >= pooldb.max_pool_fill_time:
                    update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
                    if PUSHBULLET == "True" and pool_fill_notifications == "True":
                        send_push_notification("Pool Fill Critical Stop", "Your Pool has been filling too long. Critical Stop. Check System!")
                    if SMS == "True" and pool_fill_notifications == "True":
                        send_sms_notification("Pool Fill Critical Stop - Your Pool has been filling too long. Critical Stop. Check System!")
                    if EMAIL == "True" and pool_fill_notifications == "True":
                        send_email(pooldb.alert_email, 'Pool Fill Critical Stop', 'Your Pool has been filling too long. Critical Stop. Check System!')
                    update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
                    pool_fill_valve("CRITICALCLOSE")
                    if DEBUG == "True":
                        print("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                    if LOGGING == "True":
                        logger.warn("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                pass
            else:
                if critical_stop == "True":
                    if DEBUG == "True":
                        print ("Critical Stop Enabled, pool will not fill! Check System")
                    critical_stop_enabled_warning_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_enabled_warning_sent")
                    if critical_stop_enabled_warning_sent == "False":
                        if PUSHBULLET == "True" and pool_fill_notifications == "True":
                            send_push_notification("Pool Fill Requested During Critical Stop", "Your Pool Fill is DISABLED due to Critical Stop and is LOW. Please check system!")
                        if SMS == "True" and pool_fill_notifications == "True":
                            send_sms_notification("Pool Fill Requested During Critical Stop - Your Pool Fill is DISABLED due to Critical Stop and is LOW. Please check system!")
                        if EMAIL == "True" and pool_fill_notifications == "True":
                            send_email(pooldb.alert_email, 'Pool Fill Requested During Critical Stop', 'Your Pool Fill is DISABLED due to Critical Stop and is LOW. Please check system!')
                        if LOGGING == "True":
                            logger.warn("Pool Fill Requested During Critical Stop - Your Pool Fill is DISABLED due to Critical Stop and is LOW. Please check system!")
                        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_enabled_warning_sent", True)
                    pass
                else:
                    if LOGGING == "True":
                        logger.warn("Pool LEVEL is LOW!")
                    pool_fill_valve("OPEN")
                    if DEBUG == "True":
                        print("get_pool_level_resistance() returned pool_level = LOW")


        elif get_pool_level_resistance_value <= pooldb.pool_resistance_ok_level:
            get_pool_level = "OK"
            if pool_is_filling == "True":
                    if LOGGING == "True":
                        logger.info("Pool LEVEL is back to normal!")
                    pool_fill_valve("CLOSE")
            if DEBUG == "True":
                print("get_pool_level_resistance() returned pool_level = OK")
        else:
            if pool_is_filling == "True":
                pool_fill_start_time = int(read_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time"))
                pool_fill_total_time = (current_timestamp - pool_fill_start_time) / 60
                update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", pool_fill_total_time)
                current_fill_gallons = calculate_current_fill_gallons()
                if DEBUG == "True":
                    print ("Pool has been filling for %s minutes." % pool_fill_total_time)
                    print ("Current number of gallons added to pool: %s gallons." % current_fill_gallons)
                if pool_fill_total_time >= pooldb.max_pool_fill_time:
                    update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
                    if PUSHBULLET == "True" and pool_fill_notifications == "True":
                        send_push_notification("Pool Fill Critical Stop", "Your Pool has been filling too long. Critical Stop. Check System!")
                    if SMS == "True" and pool_fill_notifications == "True":
                        send_sms_notification("Pool Fill Critical Stop - Your Pool has been filling too long. Critical Stop. Check System!")
                    if LOGGING == "True":
                        logger.warn("Pool Fill Critical Stop - Your Pool has been filling too long. Critical Stop. Check System!")
                    update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
                    pool_fill_valve("CRITICALCLOSE")
                    if DEBUG == "True":
                        print("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                    if EMAIL == "True" and pool_fill_notifications == "True":
                        send_email(pooldb.alert_email, 'Pool Fill Critical Stop', 'Your Pool has been filling too long. Critical Stop. Check System!')
                get_pool_level = "MIDWAY"
            else:
                get_pool_level = "MIDWAY"

        if DEBUG == "True":
            print("Our Pool Level is %s." % get_pool_level)


def acid_level():
    acid_level_ok = GPIO.input(acid_level_sensor_pin)
    if acid_level_ok == True:
        acid_level_status = read_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok")
        if acid_level_status == "False":
            update_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok", True)
            if LOGGING == "True":
                logger.info("Pool ACID Level is back to normal.")
        acid_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent")
        if acid_alert_sent == "True":
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent", False)
        if DEBUG == "True":
            print("Acid Level OK")
    else:
        pool_acid_level_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_acid_level_notifications")
        acid_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent")
        if acid_alert_sent == "True":
            acid_alert_sent_time = int(read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time"))
            acid_alert_sent_delta_time = (current_timestamp - acid_alert_sent_time) / 60
            time_to_next_acid_alert = (pooldb.pool_acid_alert_max_minutes - acid_alert_sent_delta_time)
            if DEBUG == "True":
                print("Acid LOW Alert sent %s minutes ago. " % acid_alert_sent_delta_time)
                print("Next Acid LOW Level Alert will be sent in %s minutes. " % time_to_next_acid_alert)
            if acid_alert_sent_delta_time >= pooldb.pool_acid_alert_max_minutes:
                if PUSHBULLET == "True" and pool_acid_level_notifications == "True":
                    send_push_notification("Pool Acid Level is STILL LOW", "Your Acid Level is STILL LOW. Please refill!")
                if SMS == "True" and pool_acid_level_notifications == "True":
                    send_sms_notification("Pool Acid Level is STILL LOW - Your Acid Level is LOW. Please refill!")
                if EMAIL == "True" and pool_acid_level_notifications == "True":
                    send_email(pooldb.alert_email, 'Pool Acid Level is LOW', 'Your Acid Level is LOW. Please refill!')
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time", current_timestamp)
                if LOGGING == "True":
                    logger.warn("Pool ACID Level STILL low. Alert sent again!")
            if DEBUG == "True":
                print("Acid Level LOW")
        else:    
            if DEBUG == "True":
                print("Acid Level LOW")
            if PUSHBULLET == "True" and pool_acid_level_notifications == "True":
                send_push_notification("Pool Acid Level is LOW", "Your Acid Level is LOW. Please refill!")
            if SMS == "True" and pool_acid_level_notifications == "True":
                send_sms_notification("Pool Acid Level is LOW - Your Acid Level is LOW. Please refill!")
            if EMAIL == "True" and pool_acid_level_notifications == "True":
                send_email(pooldb.alert_email, 'Pool Acid Level is LOW', 'Your Acid Level is LOW. Please refill!')
            update_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok", False)
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time", current_timestamp)
            if LOGGING == "True":
                logger.warn("Pool ACID Level is LOW!")



def get_pool_temp():
    if DEBUG == "True":
        print("Started get_pool_temp()")
    cnx = mysql.connector.connect(user=pooldb.username,
                                  password=pooldb.password,
                                  host=pooldb.servername,
                                  database=pooldb.emoncms_db)
    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.temp_probe_table))

    for (data) in cursor:
        get_pool_temp = float("%.2f" % data)
        cursor.close()
        if LOGGING == "True":
            logger.info('get_pool_temp returned %.2fF', get_pool_temp)
        if DEBUG == "True":
            print("get_pool_temp returned %.2fF" % get_pool_temp)

        cnx.close()
        pool_temp = float((get_pool_temp - 32) / 1.8)
        if DEBUG == "True":
             print("pool_temp in C is %.2f" % pool_temp)
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_current_temp", get_pool_temp)

    return pool_temp

    if DEBUG == "True":
        print("Completed get_pool_temp()")



def check_system_status():
    current_military_time = datetime.datetime.now().strftime('%A %b %m, %Y  %H:%M:%S')
    update_pool_sensor_status_values("pool_sensor_status", "system_status", "current_military_time", current_military_time)
    system_reset_required = read_pool_sensor_status_values("pool_sensor_status", "system_status", "system_reset_required")
    critical_stop = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop")
    
    if system_reset_required == "True":
        pool_fill_control_reset_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_control_reset_notifications")
        if LOGGING == "True":
            logger.info("System Reset Requested.")
        if DEBUG == "True":
            print("System Reset has been requested!")
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
        # Turn on our System Run LED now that everything has been reset back to normal.
        led_control(system_run_led, "True")
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_run_led", True)
        # Reset out Reset Required Value
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "system_reset_required", False)
        # Let me know the reset has been completed
        if PUSHBULLET == "True" and pool_fill_control_reset_notifications == "True":
            send_push_notification("Pool Fill Control RESET Complete", "Your Pool Fill Control has been reset to normal conditions.")
        if SMS == "True" and pool_fill_control_reset_notifications == "True":
            send_sms_notification("Pool Fill Control RESET Complete - Your Pool Fill Control has been reset to normal conditions.")
        if EMAIL == "True" and pool_fill_control_reset_notifications == "True":
            send_email(pooldb.alert_email, 'Pool Fill Control RESET Complete', 'Your Pool Fill Control has been reset to normal conditions.')
    else:
        if LOGGING == "True":
            logger.info("System Reset Status = No Reset Requested")
        if DEBUG == "True":
            print("System Reset Status = No Reset Requested")
        led_control(system_run_led, "True")
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_run_led", True)


    if critical_stop == "True":
        if LOGGING == "True":
            logger.warn("CRITICAL STOP DETECTED")
            logger.warn("Please check all systems and set [system_reset_required = True] in config file and restart program.")
            logger.warn("This will reset all systems and restart the program.")
        if DEBUG == "True":
            print("")
            print("CRITICAL STOP DETECTED")
            print("Please check all systems and set [system_reset_required = True] in config file and restart program.")
            print("This will reset all systems and restart the program.")


def is_pool_pump_running():
    """ Function to determine if our pool pump is running. """
    if DEBUG == "True":
        print("Started is_pool_pump_running()")
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
    if DEBUG == "True":
        print(
            "pool_pump_running_watts returned %s watts in use by "
            "pump." %
            pool_pump_running_watts)
    update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_watts", pool_pump_running_watts)

    if pool_pump_running_watts > pooldb.max_wattage:
        led_control(pump_run_led, "True")
        pool_pump_running = "Yes"
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
        if DEBUG == "True":
            print("PUMP_RUN_LED should be ON. This is the YELLOW LED")
    else:
        led_control(pump_run_led, "False")
        pool_pump_running = "No"
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", False)
        if DEBUG == "True":
            print("PUMP_RUN_LED should be OFF. This is the YELLOW LED")

    return pool_pump_running

# This is where we check to see if we can talk to our database. If not, stop and send notification.
def is_database_online():
    pool_database_error_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status","pool_database_error_alert_sent")
    pool_database_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_database_notifications")
    if DEBUG == "True":
        print("Started is_database_online()")
    try:
        cnx = mysql.connector.connect(user=pooldb.username,
                                      password=pooldb.password,
                                      host=pooldb.servername,
                                      database=pooldb.emoncms_db,
                                      raise_on_warnings=True)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            if LOGGING == "True":
                logger.warn("Database Error: Access Error - Check username or password.")
            if pool_database_error_alert_sent == "False":
                if PUSHBULLET == "True" and pool_database_notifications == "True":
                    send_push_notification("Pool DB ACCESS DENIED Failure!", "Pool DB ACCESS DENIED Failure. Check your username/password and other access settings and reenable the system!")
                if SMS == "True" and pool_database_notifications == "True":
                    send_sms_notification("Pool DB ACCESS DENIED Failure! - Pool DB ACCESS DENIED Failure. Check your username/password and other access settings and reenable the system!")
                if EMAIL == "True" and pool_database_notifications == "True":
                    send_email(pooldb.alert_email, 'Pool Control DB Access Denied Failure!', 'Check your username/password and other access settings and reenable the system!')
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            if DEBUG == "True":
                print(
                    "Database connection failure: Check your username and "
                    "password")
            exit()    
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            if LOGGING == "True":
                logger.warn("Database Error: Database does not exist.")
            if pool_database_error_alert_sent == "False":
                if PUSHBULLET == "True" and pool_database_notifications == "True":
                    send_push_notification("Pool DB Connection Failure!", "Pool DB does not exist. Check your settings and reenable the system!")
                if SMS == "True" and pool_database_notifications == "True":
                    send_sms_notification("Pool DB Connection Failure! - Pool DB does not exist. Check your settings and reenable the system!")
                if EMAIL == "True" and pool_database_notifications == "True":
                    send_email(pooldb.alert_email, 'Pool DB Connection Failure!', 'Pool DB does not exist. Check your settings and reenable the system!')
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            if DEBUG == "True":
                print("Database does not exist. Please check your settings.")
            exit()    
        elif err.errno == errorcode.CR_CONN_HOST_ERROR:
            if LOGGING == "True":
                logger.warn("Database Error: Cannot connect to MySQL database.")
            if pool_database_error_alert_sent == "False":
                if PUSHBULLET == "True" and pool_database_notifications == "True":
                    send_push_notification("Pool DB Connection Failure!", "Cannot Connect to MySQL Server. Check your settings and reenable the system!")
                if SMS == "True" and pool_database_notifications == "True":
                    send_sms_notification("Pool DB Connection Failure! - Cannot Connect to MySQL Server. Check your settings and reenable the system!")
                if EMAIL == "True" and pool_database_notifications == "True":
                    send_email(pooldb.alert_email, 'Pool DB Connection Failure!', 'Cannot Connect to MySQL Server. Check your settings and reenable the system!')
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            if DEBUG == "True":
                print("MySQL Server Error: Cannot connect to MySQL Server. Check connection and reset system.")
            exit()    
        else:
            if LOGGING == "True":
                logger.warn("Database Error: Unknown Error.")
            if pool_database_error_alert_sent == "False":
                if PUSHBULLET == "True" and pool_database_notifications == "True":
                    send_push_notification("Pool DB Connection Failure!", "Pool DB error. Check your settings and reenable the system!")
                if SMS == "True" and pool_database_notifications == "True":
                    send_sms_notification("Pool DB Connection Failure! - Pool DB error. Check your settings and reenable the system!")
                if EMAIL == "True" and pool_database_notifications == "True":
                    send_email(pooldb.alert_email, 'Pool DB Connection Failure!', 'Pool DB error. Check your settings and reenable the system!')
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            if DEBUG == "True":
                print(
                    "Unknown database error, please check all of your "
                    "settings.")
            exit()    
    else:
        if pool_database_error_alert_sent == "True":
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", False)
            send_push_notification("Pool DB Back Online!", "Your Pool Database is back online. System is Normal!")
            if PUSHBULLET == "True" and pool_database_notifications == "True":
                send_push_notification("Pool DB Back Online!", "Your Pool Database is back online. System is Normal!")
            if SMS == "True" and pool_database_notifications == "True":
                send_sms_notification("Pool DB Back Online - Your Pool Database is back online. System is Normal!")
            if EMAIL == "True" and pool_database_notifications == "True":
                send_email(pooldb.alert_email, 'Pool DB Back Online!', 'Your Pool Database is back online. System is Normal!')
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



# Here we go.......
def main():
    if LOGGING == "True":
        logger.info("pool_control_master started")
    is_database_online()
    mightyhat_serial_setup()
    check_system_status()
    get_pool_temp()
    is_pool_pump_running()
    check_pool_sensors()
    get_pool_level_resistance()
    get_gallons_total()
    acid_level()
    get_main_power_readings()
    pump_gpm = get_pump_gpm()
    print ("Current GPM: %s" % pump_gpm)
    pump_rpm = get_pump_rpm()
    print ("Current RPM: %s" % pump_rpm)
    get_ph_reading()
    get_orp_reading()

if __name__ == '__main__':
    main()


