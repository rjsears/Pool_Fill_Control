#!/usr/bin/python
# pool_fill_control.py
##############################################################
# Swimming Pool Fill Control Script for a Raspberry Pi 3
#
__author__ = 'Richard J. Sears'
VERSION = "V2.7 (2016-06-11)"
# richard@sears.net
##############################################################
#
# This script is part of a smart pool level monitoring system
# comprised of a moteino (moteino.com) connected to an eTape
# water level sensor. The Motenio runs a sketch that monitors
# the water level in the pool every 1 minutes and if it gets
# below a certain point, it writes a low water level bit to a
# mysql database.
#
# This script reads that bit and then makes a decision what to
# do based on the water level in the pool.
#
# If the water is low, then the script causes GPIO pin 17
# to go HIGH powering a relay that opens a sprinkler control
# valve attached to the pool. It also send a pushbullet
# notification so that you know that your pool is being filled.
#
# Once the pool level has reached the desired level, the script
# shuts off the sprinkler valve by forcing the GPIO pin LOW
# which shuts off the valve. It then sends another pushbullet
# notification letting you know is has completed filling the
# pool.
#
# There is basic error checking for running the system too long,
# and you should ktime how long it takes to fill your pool when
# it hits the low level mark and set your maxruntime somewhere
# above this time, but not TOO far above!
#
# Added blackout period for sprinkler system. Since my pool fills
# using my irrigation line, I do not want the pool to fill while
# my sprinklers are running. This would draw too much water
# pressure from my system.
#
# V2.1
# - Added logging
# - Reworked notifications to remove requirement to write a file
#   and see if the file was present. Used global variables instead.
# - Reworked overfill tracking and notification
# - Reworked manual fill to prevent manual fill while automated
#   fill is in progress. Before, requesting a manual fill while a
#   fill was in progress caused the relay to kick out and back in
#   and notifications for manual fill to go out. Now, before we do
#   a manual fill we check to see if an auto fill is in progress.
#   If there is one in progress, we just blink the button LED a
#   bunch of times and log the event.
# - Cleaned up the database check to prevent checking the pool level
#   while we are manually filling the pool.
# - Added Rachio automatic sprinkler detection.
#
#
# V2.2 (2016-05-29)
# - Added checking to see if our pool pump is running. Since (in
#   our case) we fill the pool through the same piping that we
#   filter with, we do not want the pool trying to fill while our
#   pump is running. We have a backflow valve installed to prevent
#   pressure from the pump from pushing pool water into our sprinkler
#   system (although it would have to get past a closed sprinkler
#   valve). We just don't want to try and fill the pool against the
#   pressure of the pool pump.
#
#   We have a CT on our pool panel that measures our power
#   power consumption in real time and we log that data to our emoncms
#   database (same database we log our pool level) and we are just
#   reading the power utilization (in watts) and setting a max
#   wattage that would indicate that our pump is running.
#
#   If the pump is running, automatic and manual filling is disabled
#   and we log and INFO message in the logfile.
#
# - Added some additional debug messages. Set logger.setLevel(logging.INFO)
#   to logger.setLevel(logging.DEBUG) to see the additional messages in your
#   logfile.
#
# V2.3 (2016-05-30)
# - Integrated the MightyHat (http://www.lowppowerlab.com/mightyhat)
#   with the Nokia LCD screen into the project. Now any information
#   about the status of the pool, the pool pump and the sprinklers
#   can be seen on the LCD screen as opposed to having to log into
#   the Pi to see the status.
#
#   Also updated notifications (cleanup and rearranged when and where
#   they happened) and included a lot more debugging since the script
#   is really starting to grow more and more.
#
# V2.4 (2016-06-03)
# - Updated Manual fill control to check to see if sprinklers are
#   running before allowing a manual fill.
# - Added additional system status LEDs for the following:
#     1) BLUE - Sprinklers Running
#     2) YELLOW - Pool Pump Running
#     3) GREEN - System Run
#     4) RED - System "ERROR"
#     5) BLUE2 - Pool "FILLING"
#
# V2.5 (2016-06-04)
# - Added additional DPDT switch to physically interrupt sprinkler
#   solenoid between relay and solenoid and added additional RED
#   LED to indicate when the sprinkler valve has been disabled.
#   When switch is used, power is physically removed from the fill
#   valve and we shut off the relay and send notifications as well
#   as write some log entries.
#
# - Various bug fixes
# - Cleaned up and centralized notifications.
#
# V2.6 (2016-06-05)
# - Code Optimization
# - Bug Fixes
# - Added watchdog support
#
# V2.7 (2016-06-11)
# - Added Atlas Scientific ORP and pH probes to the system and 
#   adding in code to read and write this information so we can
#   track it. I am running the USB versions of the probes to make
#   it easier to connect them to the Pi. In order to make sure
#   the assigned USB is always the same, I did the following:
# 1) connect ORP probe
# 2) run dmesg from the cli and look for the serial number and USB
#    of the connected device. 
# 3) Edit /etc/udev/rules.d/10-local.rules and put in the following:
# ACTION=="add", ATTRS{serial}=="DA00TNXX", SYMLINK+="ORP"
#
# Put your own serial number in in place of "DA00TNXX".
# 4) Do the same for your pH probe.
# Now you can use minicom, or PySerial, etc to talk to /dev/ORP or /dev/PH
#
# Right now I have created def get_ph_reading and get_orp_reading and
# currently just log it (logger.info). Evnetually I will write this
# information to my emoncms system. For me, this is just a matter of
# tracking it as I own an Autopilot system that controls my pH and ORP.
##############################################################



## This is a hobby for me. I am not a programmer and it is quite possible that you could
## flood your yard by using an automatic fill routine. THERE IS NO WARRANTY, use this script
## at your own risk!

RUN_AS_DAEMON = True  # Watchdog setup
sock_rpt = True  # Used to report only the first socket message

# Requires:
# PushBullet Python Library (https://pypi.python.org/pypi/pushbullet.py)
# Free PushBullet Account
# MySQL Python Connector http://http://dev.mysql.com/doc/connector-python/en/connector-python-introduction.html)

# Lets import some stuff!
import datetime
import logging
import os
import socket
import subprocess
import threading
import time

import RPi.GPIO as GPIO  # Import GPIO Library
import mysql.connector
import serial
from mysql.connector import errorcode
from pushbullet import Pushbullet

import alerting  # Pushbullet information
import pooldb  # Database information

#########################################
## Set up Logging
#########################################
logger = logging.getLogger('pool_fill_control')
hdlr = logging.FileHandler('/var/log/pool_fill_control.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)
logger.filemode = 'a'

##Setup our Serial so we can communicate with our Moteino MightyHat LCD Sceen
ser = serial.Serial(
    port='/dev/ttyAMA0',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1)

usbport1 = '/dev/PH'
ser1 = serial.Serial(usbport1, 9600, timeout=0)

usbport0 = '/dev/ORP'
ser2 = serial.Serial(usbport0, 9600, timeout=0)

## We have a manual fill button with a built-in LED, we set it up here
# along with the rest of our LEDs, buttons and relays.
MANUAL_FILL_BUTTON = 2  # Our Button is connected to GPIO 2 (Physical Pin 3) Builtin Resistor
MANUAL_FILL_BUTTON_LED = 11  # The LED in the button is connected to GPIO 11 (Physical Pin 23)
POOL_FILL_RELAY = 17  # Our relay for the sprinkler valve is on GPIO 17 (Physical Pin 11)
SPRINKLER_RUN_LED = 5
PUMP_RUN_LED = 13
SYSTEM_RUN_LED = 21
SYSTEM_ERROR_LED = 16
POOL_FILLING_LED = 12
POOL_FILL_VALVE_DISABLED = 3
POOL_FILL_VALVE_DISABLED_LED = 4


def init():
    # get the watchdog timeout period set in the systemd service file
    if RUN_AS_DAEMON:  # this will only work if started by systemd
        wd_usec = os.environ.get('WATCHDOG_USEC', None)
        if wd_usec == None or wd_usec == 0:
            logger.error("Pool Fill Control Terminating : incorrect watchdog interval sequence.")
            exit(1)
    else:  # used when invoked by the shell
        wd_usec = 20000000  # 20 seconds

    wd_usec = int(wd_usec)
    # use half the time-out value in seconds for the watchdog ping routine to
    # account for Linux housekeeping chores
    wd_ping = wd_usec / 1000000 / 2
    ## Setup and initially set some global variables
    global current_run_time
    current_run_time = 0
    global pool_is_filling
    pool_is_filling = "No"
    global max_run_time_exceeded
    max_run_time_exceeded = "No"
    global alertsent
    alertsent = "No"
    global overfill_alert_sent
    overfill_alert_sent = "No"
    global pool_pump_running_watts
    pool_pump_running_watts = 0
    global sprinkler_status
    global pool_fill_valve_disabled
    global pool_fill_valve_alert_sent
    pool_fill_valve_alert_sent = "No"
    global MANUAL_FILL_BUTTON_LED_ON
    MANUAL_FILL_BUTTON_LED_ON = False

    try:
        ## Set up all of our GPIO Stuff here
        GPIO.setwarnings(False)  # Don't tell me about GPIO warnings.
        GPIO.setmode(GPIO.BCM)  # Use BCM Pin Numbering Scheme

        ## Setup our GPIO Pins
        GPIO.setup(POOL_FILL_RELAY, GPIO.OUT)
        GPIO.output(POOL_FILL_RELAY, True)  # Set inital state of our relay to off
        GPIO.setup(MANUAL_FILL_BUTTON,
                   GPIO.IN)  # Make button an input,  since we are using GPIO 2, it has pull up resistor already
        GPIO.setup(MANUAL_FILL_BUTTON_LED, GPIO.OUT)  # Make LED  an Output
        GPIO.output(MANUAL_FILL_BUTTON_LED, False)
        GPIO.setup(SPRINKLER_RUN_LED, GPIO.OUT)
        GPIO.output(SPRINKLER_RUN_LED, False)
        GPIO.setup(PUMP_RUN_LED, GPIO.OUT)
        GPIO.output(PUMP_RUN_LED, False)
        GPIO.setup(SYSTEM_RUN_LED, GPIO.OUT)
        GPIO.output(SYSTEM_RUN_LED, False)
        GPIO.setup(SYSTEM_ERROR_LED, GPIO.OUT)
        GPIO.output(SYSTEM_ERROR_LED, False)
        GPIO.setup(POOL_FILLING_LED, GPIO.OUT)
        GPIO.output(POOL_FILLING_LED, False)
        GPIO.setup(POOL_FILL_VALVE_DISABLED, GPIO.IN)
        GPIO.setup(POOL_FILL_VALVE_DISABLED_LED, GPIO.OUT)
        GPIO.output(POOL_FILL_VALVE_DISABLED_LED, False)

        # Setup our event detection for our manual fill button as well as our fill valve disable switch
        GPIO.add_event_detect(MANUAL_FILL_BUTTON, GPIO.RISING, callback=manual_fill_pool, bouncetime=1500)
        GPIO.add_event_detect(POOL_FILL_VALVE_DISABLED, GPIO.BOTH, callback=is_pool_fill_valve_disabled, bouncetime=500)

        # notify systemd that we've finished the initialization
        retval = sd_notify(0, "READY=1")
        # check for a fatal error
        if retval <> 0:
            logger.error("Fatal sd_notify() error for script start".format(retval))
            os._exit(1)  # force the exit to the OS

        # start the first ping to the systemd sw watchdog and check for errors
        retval = sd_notify(0, "WATCHDOG=1")
        if retval <> 0:
            logger.error("Fatal sd_notify() error for watchdog ping, retval={0}".format(retval))
            os._exit(1)  # force the exit to the OS

    except Exception as e:
        logger.error("Exception in init()! DIE".format(e))
        os._exit(1)  # force the exit to the OS


def sd_notify(unset_environment, s_cmd):
    global sock_rpt

    sock = None

    if not RUN_AS_DAEMON:
        print "Not running as a daemon, cannot communicate with systemd socket"
        return 0

    try:
        if not s_cmd:
            logger.error("Pool Fill Error : missing command to send.")
            return 1

        s_adr = os.environ.get('NOTIFY_SOCKET', None)
        if sock_rpt:  # report this only one time
            logger.info("Notify socket = {0}".format(str(s_adr)))
            # this will normally return : /run/systemd/notify
            sock_rpt = False

        if not s_adr:
            logger.error("Error, missing socket.")
            return 1

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.sendto(s_cmd, s_adr)
        # sendto() returns number of bytes send
        if sock.sendto(s_cmd, s_adr) == 0:
            logger.error("Error, incorrect sock.sendto return value")
            return 1

    except exception as e:
        logger.error("Unexpecgted Exception in sd_notify".format(e))
        os._exit(1)  # force the exit to the OS

    finally:
        # terminate the socket connection
        if sock:
            sock.close()
        if unset_environment:
            if 'NOTIFY_SOCKET' in os.environ:
                del os.environ['NOTIFY_SOCKET']
    return 0  # so we can test the return value for a successful execution


## LED Management

# Blinking
def blink_led(pin, numTimes, speed):
    for i in range(0, numTimes):
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed)


# ON/OFF
def led_control(led, onoff):
    if onoff == "ON":
        GPIO.output(led, True)
    elif onoff == "OFF":
        GPIO.output(led, False)


# Let's reach out and get our current pH and ORP
def get_ph_reading():
    line ="" 
    count = 1
    while (count < 2):
       data = ser1.read()
       if(data == "\r"):
          ph_value = float(line)
          logger.info("Current PH Reading is %s" % ph_value)
          line = ""
          count = count + 1
       else:
          line = line + data

def get_orp_reading():
    line = ""
    count = 1
    while (count < 2):
       data = ser2.read()
       if(data == "\r"):
          orp_value = float(line)
          logger.info("Current ORP Reading is %s" % orp_value)
          line = ""
          count = count + 1
       else:
          line = line + data


# This is where we set up our notifications. I use Pushbullet which is free and very powerful. Visit http://www.pushbullet.com for a free account.
# Once you have your free account, enter your API information in the alerting.py file and restart the script.
pb = Pushbullet(alerting.pushbilletAPI)


def send_notification(status):
    global alertsent
    global overfill_alert_sent
    global pool_fill_valve_alert_sent
    if status == "FILLING" and alertsent == "No":
        push = pb.push_note("Swimming Pool is Refilling Automatically",
                            "Your swimming pool water level is low and is being refilled.")
        alertsent = "Yes"
        logger.info('PushBullet Notification Sent  - Pool is Automatically Refilling')
    elif status == "DONE_FILLING" and alertsent == "Yes":
        push = pb.push_note("Swimming Pool Level OK",
                            "Swimming pool water level back to normal. Automatic Refilling Complete.")
        alertsent == "No"
        logger.info('PushBullet Notification Sent - Pool is done refilling Automatically')
    elif status == "MANUAL_FILL":
        push = pb.push_note("Swimming Pool Manual Fill", "Your swimming pool is being manually filled")
        logger.info('PushBullet Notification Sent - Manual Fill Started')
    elif status == "MANUAL_FILL_COMPLETE":
        push = pb.push_note("Swimming Pool Manual Fill Complete",
                            "Manaul fill of your swimming pool has been completed")
        logger.info('PushBullet Notification Sent - Manual Fill Complete')
    elif status == "POOL_OVERFILL" and overfill_alert_sent == "No":
        push = pb.push_note("Swimming Pool Fill Failure",
                            "Your swimming pool might be overfilling! The valve has been DISABLED, you need to reenable it!")
        logger.error('PushBullet Notification Sent - Pool might be overfilling')
    elif status == "POOL_FILL_VALVE_DISABLED" and pool_fill_valve_alert_sent == "No":
        push = pb.push_note("Pool Fill Valve - DISABLED",
                            "Your swimming pool fill valve has been manually DISABLED, you need to reenable it to fill your pool!")
        logger.error('PushBullet Notification Sent - Pool fill valve manually disabled')
        pool_fill_valve_alert_sent == "Yes"
    elif status == "POOL_FILL_VALVE_REENABLED" and pool_fill_valve_alert_sent == "Yes":
        push = pb.push_note("Pool Fill Valve - ENABLED",
                            "Your swimming pool fill valve has been REENABLED!")
        logger.error('PushBullet Notification Sent - Pool fill valve manually reenabled')
        pool_fill_valve_alert_sent == "No"
    elif status == "STARTUP_OK":
        push = pb.push_note("Pool Fill Control - Startup",
                            "Your Pool Filling Control system has started successfully!")
        logger.debug('PushBullet Notification Sent - Pool fill control started successfully')
        pool_fill_valve_alert_sent == "No"


def start_ok():
    ## Go ahead and send a notification that we started OK!
    if alerting.PoolAlerting == "True":
        send_notification('STARTUP_OK')
    ## If we have a MightyHat with an LCD screen, we can output a message there as well....
    if pooldb.MightyHat == "True":
        ser.write('PFC_START_OK')
    ## Log startup
    logger.info('pool_fill_control.py %s started', VERSION)


def pfv_disabled():
    ## Let take a quick look at the switch that controls our fill valve. Has it been disabled? If so, send a notification
    ## and log the error.
    global pool_fill_valve_disabled
    pool_fill_valve_disabled = GPIO.input(POOL_FILL_VALVE_DISABLED)
    if pool_fill_valve_disabled == True:
        logger.error(
            'Pool Fill Valve has been DISABLED. System is OFFLINE. Reenable Pool Fill Valve to fill your pool!')
        led_control(POOL_FILL_VALVE_DISABLED_LED, "ON")
        logger.debug("POOL_FILL_VALVE_DISABLED_LED should be ON. This is a RED LED.")
        if alerting.PoolAlerting == "True":
            send_notification('POOL_FILL_VALVE_DISABLED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_MANUALLY_DISABLED')


def get_sprinkler_status():
    # I use this to keep the pool from filling while my sprinklers are running. You could also use this as a means of
    # creating a 'blackout' period during which time you do not want your pool filled.
    # This is the sprinkler start and stop times. Python is a bit weird in that you cannot use 0900 or 0800 because
    # of the leading '0'. Any other time is ok.
    # Use military time but DO NOT use leading zeros!
    if pooldb.sprinkler_type == "Timer":
        SprinklerStart = int(400)
        SprinklerStop = int(1000)

        current_military_time = int(datetime.datetime.now().strftime('%H%M'))
        logger.debug('Current military time is being reported as %s.', current_military_time)

        if SprinklerStart < current_military_time < SprinklerStop:
            sprinklers_on = "Yes"
            logger.debug('Sprinklers running. (TIMER)')
            led_control(SPRINKLER_RUN_LED, "ON")
            logger.debug('SPRINKLER_RUN_LED should be ON. This is a BLUE LED')

        else:
            sprinklers_on = "No"
            logger.debug('Sprinklers are not running (TIMER).')
            led_control(SPRINKLER_RUN_LED, "OFF")
            logger.debug('SPRINKLER_RUN_LED should be OFF. This is a BLUE LED')

        return sprinklers_on
    else:
        output = subprocess.check_output(pooldb.rachio_url, shell=True)
        if output == "{}":
            sprinklers_on = "No"
            logger.debug('Sprinklers are not running (RACHIO).')
            led_control(SPRINKLER_RUN_LED, "OFF")
            logger.debug('SPRINKLER_RUN_LED should be OFF. This is a BLUE LED')
        else:
            sprinklers_on = "Yes"
            logger.debug('Sprinklers running. (RACHIO)')
            led_control(SPRINKLER_RUN_LED, "ON")
            logger.debug('SPRINKLER_RUN_LED should be ON. This is a BLUE LED')

        return sprinklers_on


# This turns the sprinkler valve on or off when called
def fill_pool_auto(fill_now):
    global pool_is_filling
    global current_run_time
    if fill_now == "START":
        GPIO.output(POOL_FILL_RELAY, False)  # Turns on the sprinkler valve
        pool_is_filling = "Auto"
        logger.info('Pool AUTOMATIC fill started.')
        led_control(POOL_FILLING_LED, "ON")
        logger.debug('POOL_FILLING_LED should be ON. This is a BLUE LED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_AUTO_FILL')
            logger.debug('Pool Automatic Fill started (PFC_AUTO_FILL) sent to MightyHat')
        if alerting.PoolAlerting == "True":
            send_notification('FILLING')
    elif fill_now == "STOP":
        GPIO.output(POOL_FILL_RELAY, True)  # Shuts off the sprinkler valve
        pool_is_filling = "No"
        logger.info('Pool AUTOMATIC fill completed.')
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        current_run_time = 0
        if pooldb.MightyHat == "True":
            ser.write('PFC_FILL_DONE')
            logger.debug('Pool filling complete (PFC_FILL_DONE) sent to MightyHat')
        if alerting.PoolAlerting == "True":
            send_notification('DONE_FILLING')
    elif fill_now == "FORCE_STOP":
        GPIO.output(POOL_FILL_RELAY, True)  # Shuts off the sprinkler valve
        pool_is_filling = "No"
        logger.warning('Pool AUTOMATIC fill FORCE STOPPED.')
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        led_control(SYSTEM_ERROR_LED, "ON")
        logger.debug('SYSTEM_ERROR_LED should be ON. This is the RED LED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_OVERFILL')
            logger.debug('Pool Automatic Fill Force Stopped (PFC_OVERFILL) sent to MightyHat')
    elif fill_now == "MANUAL_VALVE_DISABLED":
        GPIO.output(POOL_FILL_RELAY, True)  # Shuts off the sprinkler valve
        pool_is_filling = "No"
        logger.warning('Pool AUTOMATIC fill FORCE STOPPED - Fill Valve has been manually disabled.')
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        led_control(SYSTEM_ERROR_LED, "ON")
        logger.debug('SYSTEM_ERROR_LED should be ON. This is the RED LED')


# This turns the sprinkler valve on or off when manual button is pushed.
def fill_pool_manual(fill_now):
    global pool_is_filling
    global current_run_time
    global MANUAL_FILL_BUTTON_LED_ON
    if fill_now == "START":
        GPIO.output(POOL_FILL_RELAY, False)  # Turns on the sprinkler valve
        pool_is_filling = "Manual"
        logger.info('Pool MANUAL fill started.')
        if pooldb.MightyHat == "True":
            ser.write('PFC_MAN_FILL')
            logger.debug('Pool manual fill started (PFC_MAN_FILL) sent to MightyHat')
    elif fill_now == "STOP":
        GPIO.output(POOL_FILL_RELAY, True)  # Shuts off the sprinkler valve
        pool_is_filling = "No"
        logger.info('Pool MANUAL fill completed.')
        current_run_time = 0
        if pooldb.MightyHat == "True":
            ser.write('PFC_FILL_DONE')
            logger.debug('Pool Fill Complete (PFC_FILL_DONE) sent to MightyHat')
    elif fill_now == "MANUAL_VALVE_DISABLED":
        GPIO.output(POOL_FILL_RELAY, True)  # Shuts off the sprinkler valve
        pool_is_filling = "No"
        led_control(MANUAL_FILL_BUTTON_LED, "OFF")
        MANUAL_FILL_BUTTON_LED_ON = False
        logger.warning('Pool MANUAL fill FORCE STOPPED - Fill Valve has been manually disabled.')
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        led_control(SYSTEM_ERROR_LED, "ON")
        logger.debug('SYSTEM_ERROR_LED should be ON. This is the RED LED')


# Called from the fill_pool() routine and keeps track of how many times we have checked the pool level. 
# We can then decide what to do if it is taking too long to fill the pool (or the sensor node died before
# it could update the database). In this case, it simply flags the max_run_time_exceeded variable, shuts off
# the water, logs the error and waits for you to restart the program which clears the variable. 
def max_run_time():
    global max_run_time_exceeded
    global current_run_time
    global overfill_alert_sent
    current_run_time += 1
    logger.debug('Current fill run time is %s', current_run_time)

    if current_run_time >= pooldb.maxruntime:
        logger.error('Pool Maxruntime exceeded! Check for errors and restart program')
        max_run_time_exceeded = "Yes"
        if alerting.PoolAlerting == "True":
            send_notification('POOL_OVERFILL')
            overfill_alert_sent == "Yes"


# This connectes to our database and gets our pool level.
def pool_level():
    global pool_pump_running_watts
    global pool_is_filling
    global max_run_time_exceeded
    global sprinkler_status
    global pool_fill_valve_disabled
    get_ph_reading()
    get_orp_reading()
    sprinkler_status = get_sprinkler_status()
    sd_notify(0,
              "WATCHDOG=1")  # Ping the watchdog once per check. It is set to restart the script if no notification within 70 seconds.
    logger.debug("Watchdog Ping Sent")
    if MANUAL_FILL_BUTTON_LED_ON == True or pool_fill_valve_disabled == True:  # Why bother checking if we are manually filling the pool....?
        if MANUAL_FILL_BUTTON_LED_ON == True:
            logger.debug("pool_level function BYPASSED, Manual fill is in progress.")
        elif pool_fill_valve_disabled == True:
            logger.debug("pool_level function BYPASSED, pool fill valve has been manually disabled")
        pass
    else:
        try:
            cnx = mysql.connector.connect(user=pooldb.username, password=pooldb.password, host=pooldb.servername,
                                          database=pooldb.emoncms_db)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error('Database connection failure: Check your username and password')
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                logger.error('Database does not exist. Please check your settings.')
            else:
                logger.error('Unknown database error, please check all of your settings.')
        else:
            cursor = cnx.cursor(buffered=True)
            cursor.execute("SELECT data FROM feed_222 ORDER by time DESC LIMIT 1")

            for (data) in cursor:
                get_pool_level = ("%1.0f" % data)
                cursor.close()
                logger.debug('get_pool_level returned %s', get_pool_level)

            cursor = cnx.cursor(buffered=True)
            cursor.execute("SELECT data FROM feed_153 ORDER by time DESC LIMIT 1")

            for (data) in cursor:
                pool_pump_running_watts = int("%1.0f" % data)
                cursor.close()
                logger.debug('pool_pump_running_watts returned %s watts in use by pump.', pool_pump_running_watts)

            if pool_pump_running_watts > pooldb.max_wattage:
                led_control(PUMP_RUN_LED, "ON")
                logger.debug('PUMP_RUN_LED should be ON. This is the YELLOW LED')
            else:
                led_control(PUMP_RUN_LED, "OFF")
                logger.debug('PUMP_RUN_LED should be OFF. This is the YELLOW LED')

            if get_pool_level == "1" and pooldb.MightyHat == "True":
                logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
                ser.write('PFC_LEVEL_OK')
                logger.debug('Pool Level OK (PFC_LEVEL_OK) sent to MightyHat')

            if get_pool_level == "1" and pool_is_filling == "Auto":
                fill_pool_auto('STOP')

            elif get_pool_level == "0":
                if pooldb.MightyHat == "True":
                    ser.write('PFC_LEVEL_LOW')
                    logger.debug('Pool Level Low (PFC_LEVEL_LOW) sent to MightyHat')
                sprinkler_status = get_sprinkler_status()
                if sprinkler_status == "Yes":
                    logger.info('Sprinklers are running, we cannot fill the pool at this time.')
                    if pooldb.MightyHat == "True":
                        ser.write('PFC_SPRINKLERS')
                        logger.debug('Sprinklers are running (PFC_SPRINKLERS) sent to MightyHat')
                    pass
                elif pool_pump_running_watts > pooldb.max_wattage:
                    logger.info('Pool pump is running, we cannot fill the pool at this time.')
                    if pooldb.MightyHat == "True":
                        ser.write('PFC_PUMP')
                        logger.debug('Pool pump is running (PFC_PUMP) sent to MightyHat')
                    pass
                else:
                    max_run_time()
                    if max_run_time_exceeded == "Yes":
                        fill_pool_auto('FORCE_STOP')
                    elif pool_is_filling == "No":
                        fill_pool_auto('START')

            cnx.close()
    threading.Timer(pooldb.checktime, pool_level).start()


# This manages our manaul fill pushbutton
def manual_fill_pool(button):
    global pool_pump_running_watts
    global pool_is_filling
    global sprinkler_status
    global MANUAL_FILL_BUTTON_LED_ON
    global pool_fill_valve_disabled
    if all([MANUAL_FILL_BUTTON_LED_ON == False, pool_is_filling == "No",
            pool_pump_running_watts <= pooldb.max_wattage, sprinkler_status == "No",
            pool_fill_valve_disabled == False]):
        GPIO.output(MANUAL_FILL_BUTTON_LED, True)
        MANUAL_FILL_BUTTON_LED_ON = True
        fill_pool_manual('START')
        led_control(POOL_FILLING_LED, "ON")
        logger.debug('POOL_FILLING_LED should be ON. This is a BLUE LED')
        if alerting.PoolAlerting == "True":
            send_notification('MANUAL_FILL')
    elif pool_is_filling == "Manual":
        GPIO.output(MANUAL_FILL_BUTTON_LED, False)
        MANUAL_FILL_BUTTON_LED_ON = False
        fill_pool_manual('STOP')
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        if alerting.PoolAlerting == "True":
            send_notification('MANUAL_FILL_COMPLETE')
    else:
        blink_led(MANUAL_FILL_BUTTON_LED, 7, 0.1)
        if sprinkler_status == "Yes":
            logger.info("Manual fill attempted while sprinklers were running.")
        elif pool_pump_running_watts >= pooldb.max_wattage:
            logger.info("Manual fill attempted while pool pump was running.")
        elif pool_is_filling == "Auto":
            logger.info("Manual fill attempted while pool was automatically filling.")
        elif pool_fill_valve_disabled:
            logger.info("Manual fill attempted with pool valve manually disabled.")


def is_pool_fill_valve_disabled(channel):
    global pool_fill_valve_disabled
    global pool_is_filling
    pool_fill_valve_disabled = GPIO.input(POOL_FILL_VALVE_DISABLED)
    if pool_fill_valve_disabled == True:
        if pool_is_filling == "Auto":
            fill_pool_auto('MANUAL_VALVE_DISABLED')
        else:
            fill_pool_manual('MANUAL_VALVE_DISABLED')
        logger.info("Manual pool fill valve has been DISABLED! Reenable to fill pool.")
        led_control(POOL_FILL_VALVE_DISABLED_LED, "ON")
        led_control(SYSTEM_ERROR_LED, "ON")
        logger.debug("POOL_FILL_VALVE_DISABLED_LED should be ON. This is a RED LED.")
        logger.debug("SYSTEM_ERROR_LED should be ON. This is a RED LED.")
        if alerting.PoolAlerting == "True":
            send_notification('POOL_FILL_VALVE_DISABLED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_MANUALLY_DISABLED')
    elif not (pool_fill_valve_disabled):
        print ("Pool Fill Valve has been Reenabled")
        led_control(POOL_FILL_VALVE_DISABLED_LED, "OFF")
        led_control(SYSTEM_ERROR_LED, "OFF")
        logger.debug("POOL_FILL_VALVE_DISABLED_LED should be OFF. This is a RED LED.")
        logger.debug("SYSTEM_ERROR_LED should be OFF. This is a RED LED.")
        logger.info("Manual pool fill valve has been ENABLED.")
        pool_is_filling = "No"
        if alerting.PoolAlerting == "True":
            send_notification('POOL_FILL_VALVE_REENABLED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_MANUALLY_REENABLED')
        pool_level()


def main():
    init()
    start_ok()
    pfv_disabled()
    led_control(SYSTEM_RUN_LED, "ON")
    pool_level()


if __name__ == '__main__':
    main()
