#!/usr/bin/python

# pool_fill_control.py
##############################################################
# Swimming Pool Fill Control Script for a Raspberry Pi 3
#
# V2.4 (2016-06-03)
# Richard J. Sears
# richard@sears.net
##############################################################
#
# This script is part of a smart pool level monitoring system
# comprised of a moneino (moteino.com) connected to an eTape
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
##############################################################



## This is a hobby for me. I am not a programmer and it is quite possible that you could
## flood your yard by using an automatic fill routine. THERE IS NO WARRANTY, use this script
## at your own risk!




# Requires:
# PushBullet Python Library (https://pypi.python.org/pypi/pushbullet.py)
# Free PushBullet Account
# MySQL Python Connector http://http://dev.mysql.com/doc/connector-python/en/connector-python-introduction.html)



import datetime
import subprocess
import threading
import time

import RPi.GPIO as GPIO  # Import GPIO Library
import alerting  # Pushbullet information
import mysql.connector
import pooldb  # Database information
import serial
from mysql.connector import errorcode
from pushbullet import Pushbullet

#########################################
## Set up Logging
#########################################
import logging

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

## Log startup
logger.info('pool_fill_control.py V2.2 (2016-05-29) Started')

## Set up all of our GPIO Stuff here
GPIO.setwarnings(False)  # Don't tell me about GPIO warnings.
GPIO.setmode(GPIO.BCM)  # Use BCM Pin Numbering Scheme

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






## Setup our GPIO Pins
GPIO.setup(POOL_FILL_RELAY, GPIO.OUT)
GPIO.output(POOL_FILL_RELAY, True)  # Set inital state of our relay to off
GPIO.setup(MANUAL_FILL_BUTTON, GPIO.IN)  # Make button an input,  since we are using GPIO 2, it has pull up resistor already
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



## Set the Button LED initially off
MANUAL_FILL_BUTTON_LED_ON = False

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

# This is where we set up our notifications. I use Pushbullet which is free and very powerful. Visit http://www.pushbullet.com for a free account.
# Once you have your free account, enter your API information in the alerting.py file and restart the script.
pb = Pushbullet(alerting.pushbilletAPI)


def send_notification(fill_status):
    global alertsent
    global overfill_alert_sent
    if fill_status == "FILLING" and alertsent == "No":
        push = pb.push_note("Swimming Pool is Refilling Automatically",
                            "Your swimming pool water level is low and is being refilled.")
        alertsent = "Yes"
        logger.info('PushBullet Notification Sent  - Pool is Automatically Refilling')
    elif fill_status == "DONE_FILLING" and alertsent == "Yes":
        push = pb.push_note("Swimming Pool Level OK",
                            "Swimming pool water level back to normal. Automatic Refilling Complete.")
        alertsent == "No"
        logger.info('PushBullet Notification Sent - Pool is done refilling Automatically')
    elif fill_status == "MANUAL_FILL":
        push = pb.push_note("Swimming Pool Manual Fill", "Your swimming pool is being manually filled")
        logger.info('PushBullet Notification Sent - Manual Fill Started')
    elif fill_status == "MANUAL_FILL_COMPLETE":
        push = pb.push_note("Swimming Pool Manual Fill Complete",
                            "Manaul fill of your swimming pool has been completed")
        logger.info('PushBullet Notification Sent - Manual Fill Complete')
    elif fill_status == "POOL_OVERFILL" and overfill_alert_sent == "No":
        push = pb.push_note("Swimming Pool Fill Failure",
                            "Your swimming pool might be overfilling! The valve has been DISABLED, you need to reenable it!")
        logger.error('PushBullet Notification Sent - Pool might be overfilling')


## Go ahead and send a notification that we started OK!
if (alerting.PoolAlerting) == "True":
    push = pb.push_note("Pool Fill Control - Startup", "Your Pool Filling Control has started successfully!")

## If we have a MightyHat with an LCD screen, we can output a message there as well....
if pooldb.MightyHat == "True":
    ser.write('PFC_START_OK')


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

        if current_military_time > SprinklerStart and current_military_time < SprinklerStop:
            sprinklers_on = "Yes"
            logger.debug('Sprinklers running. (TIMER)')
            led_control(SPRINKLER_RUN_LED, "ON")
            logger.debug('SPRINKLER_RUN_LED should be ON. This is a BLUE LED')

        else:
            sprinklers_on = "No"
            logger.debug('Sprinklers are not running (TIMER).')
            led_control(SPRINKLER_RUN_LED, "OFF")
            logger.debug('SPRINKLER_RUN_LED should be OFF. This is a BLUE LED')

        return (sprinklers_on)
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

        return (sprinklers_on)




# This turns the sprinkler valve on or off when called
def fill_pool_auto(fill_now):
    global pool_is_filling
    if fill_now == "START":
        GPIO.output(POOL_FILL_RELAY, False)  # Turns on the sprinkler valve
        pool_is_filling = "Auto"
        logger.info('Pool AUTOMATIC fill started.')
        led_control(POOL_FILLING_LED, "ON")
        logger.debug('POOL_FILLING_LED should be ON. This is a BLUE LED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_AUTO_FILL')
            logger.debug('Pool Automatic Fill started (PFC_AUTO_FILL) sent to MightyHat')
        if (alerting.PoolAlerting) == "True":
            send_notification('FILLING')
    elif fill_now == "STOP":
        GPIO.output(POOL_FILL_RELAY, True)  # Shuts off the sprinkler valve
        pool_is_filling = "No"
        logger.info('Pool AUTOMATIC fill completed.')
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_FILL_DONE')
            logger.debug('Pool filling complete (PFC_FILL_DONE) sent to MightyHat')
        if (alerting.PoolAlerting) == "True":
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


# This turns the sprinkler valve on or off when manual button is pushed.
def fill_pool_manual(fill_now):
    global pool_is_filling
    if fill_now == "START":
        GPIO.output(POOL_FILL_RELAY, False)  # Turns on the sprinkler valve
        pool_is_filling = "Yes"
        logger.info('Pool MANUAL fill started.')
        if pooldb.MightyHat == "True":
            ser.write('PFC_MAN_FILL')
            logger.debug('Pool manual fill started (PFC_MAN_FILL) sent to MightyHat')
    elif fill_now == "STOP":
        GPIO.output(POOL_FILL_RELAY, True)  # Shuts off the sprinkler valve
        pool_is_filling = "No"
        logger.info('Pool MANUAL fill completed.')
        if pooldb.MightyHat == "True":
            ser.write('PFC_FILL_DONE')
            logger.debug('Pool Fill Complete (PFC_FILL_DONE) sent to MightyHat')


# Called from the fill_pool() routine and keeps track of how many times we have checked the pool level. 
# We can then decide what to do if it is taking too long to fill the pool (or the sensor node died before
# it could update the database). In this case, it simply flags the max_run_time_exceeded variable, shuts off
# the water, logs the error and waits for you to restart the program which clears the variable. 
def max_run_time():
    global max_run_time_exceeded
    global current_run_time
    global overfill_alert_sent
    current_run_time = current_run_time + 1
    logger.debug('Current fill run time is %s', current_run_time)

    if current_run_time >= pooldb.maxruntime:
        logger.error('Pool Maxruntime exceeded! Check for errors and restart program')
        max_run_time_exceeded = "Yes"
        if (alerting.PoolAlerting) == "True":
            send_notification('POOL_OVERFILL')
            overfill_alert_sent == "Yes"


# This connectes to our database and gets our pool level.
def pool_level():
    global pool_pump_running_watts
    global pool_is_filling
    global max_run_time_exceeded
    global sprinkler_status
    sprinkler_status = get_sprinkler_status()
    if MANUAL_FILL_BUTTON_LED_ON == True:  # Why bother checking if we are manually filling the pool....?
        pass
    else:
        try:
            cnx = mysql.connector.connect(user=(pooldb.username), password=(pooldb.password), host=(pooldb.servername),
                                          database=(pooldb.emoncms_db))
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
                get_pool_level = ("%1.0f" % (data))
                cursor.close()
                logger.debug('get_pool_level returned %s', get_pool_level)

            cursor = cnx.cursor(buffered=True)
            cursor.execute("SELECT data FROM feed_153 ORDER by time DESC LIMIT 1")

            for (data) in cursor:
                pool_pump_running_watts = int("%1.0f" % (data))
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
    if all([MANUAL_FILL_BUTTON_LED_ON == False, pool_is_filling == "No",
            pool_pump_running_watts <= pooldb.max_wattage, sprinkler_status == "No"]):
        GPIO.output(MANUAL_FILL_BUTTON_LED, True)
        MANUAL_FILL_BUTTON_LED_ON = True
        fill_pool_manual('START')
        led_control(POOL_FILLING_LED, "ON")
        logger.debug('POOL_FILLING_LED should be ON. This is a BLUE LED')
        if (alerting.PoolAlerting) == "True":
            send_notification('MANUAL_FILL')
    elif pool_is_filling == "Yes":
        GPIO.output(MANUAL_FILL_BUTTON_LED, False)
        MANUAL_FILL_BUTTON_LED_ON = False
        fill_pool_manual('STOP')
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        if (alerting.PoolAlerting) == "True":
            send_notification('MANUAL_FILL_COMPLETE')
    else:
        blink_led(MANUAL_FILL_BUTTON_LED, 7, 0.1)
        logger.info('Manual fill attempted while pool was automatically filling or  pool pump/sprinklers were running!')


# Manage blinking some LEDs
def blink_led(pin, numTimes, speed):
    for i in range(0, numTimes):
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed)

def led_control(led, onoff):
    if onoff == "ON": 
        GPIO.output(led, True)  
    elif onoff =="OFF":
        GPIO.output(led, False)

def main():
    led_control(SYSTEM_RUN_LED, "ON")
    pool_level()
    GPIO.add_event_detect(MANUAL_FILL_BUTTON, GPIO.RISING, callback=manual_fill_pool, bouncetime=1500)

main()

