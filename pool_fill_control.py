#!/usr/bin/python
# Set DEBUG = 1 to run this from the command line. It will bypass the watchdog support
# and enable all debug printing to STDOUT.

DEBUG = 0

# pool_fill_control.py
##############################################################
# Swimming Pool Fill Control Script for a Raspberry Pi 3
#
__author__ = 'Richard J. Sears'
VERSION = "V3.1 (2016-10-08)"
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
#
#
# V2.8 (2016-06-13)
# - Changed the way that I read pH and ORP. Also writes the pH and ORP
#   values to my two emoncms servers (one local and one remote).
#
# V2.9 (2016-06-18)
# - Eliminated alerting.py file, added contents to pooldb.py file.
# - Added a lot of DEBUG printing to STDOUT if DEBUG == 1 is set. 
# - Moved pool_level and pump_running_watts table defs to pooldb.py
#   so that you do not have to modify table definitions in main script.
# - Added in temperature compensation function for pH readings if you
#   have a pool water temp probe. Configuration is done in pooldb.py
#
# V3.0 (2016-09-04)
# - Added a second relay to control the sprinkler transformer power
#   so that the transformer is not powered up all of the time but is
#   only powered up when we need to fill the pool.
# - Added a new function to control both of the relays at once.
# - Added additional debugging and logging.
#
# V3.1 (2016-10-08)
# - Added new sensor checking function to check that our temp and
#   pool level sensors are responding as required and included
#   notifications if they exceed a certain number of timeouts
#   or their battery voltage drops too low. Also updated pool
#   fill to stop automatically if we lose communication with 
#   with our pool level sensor.
#
# - Updated pool_fill() to include calls to differnt functions
#   to streamline that particular function. Also cuts down on
#   a couple of global variables. Need to continue to clean
#   this up as I go through and optimize the code. 
#
# - Changed the way we get the pool level. We used to have a 0
#   or a 1 programmed to be sent directly from the sensor. We
#   would then make a decision to fill the pool based on the 
#   reading from the sensor. Now I output the actual resistance
#   from the sensor to the database and using these values we 
#   can change the level of when we want to fill the pool 
#   within pooldb.py instead of having to physically reflash
#   the pool_level arduino sensor.
##############################################################


## This is a hobby for me. I am not a programmer and it is quite possible that you could
## flood your yard by using an automatic fill routine. THERE IS NO WARRANTY, use this script
## at your own risk!


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
import requests
import serial
from mysql.connector import errorcode
from pushbullet import Pushbullet

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

global pool_level_sensor_alert_sent
pool_level_sensor_alert_sent = "No"

global pool_level_sensor_batt_low_alert_sent
pool_level_sensor_batt_low_alert_sent = "No"

global pool_temp_sensor_alert_sent
pool_temp_sensor_alert_sent = "No"

global pool_temp_sensor_batt_low_alert_sent
pool_temp_sensor_batt_low_alert_sent = "No"

global max_pool_level_sensor_timeouts_exceeded
max_pool_level_sensor_timeouts_exceeded = "No"

global pool_level_sensor_timeout_alert_sent
pool_level_sensor_timeout_alert_sent = "No"

global current_pool_level_sensor_timeouts
current_pool_level_sensor_timeouts = 0



## We have a manual fill button with a built-in LED, we set it up here
# along with the rest of our LEDs, buttons and relays.
MANUAL_FILL_BUTTON = 2  # Our Button is connected to GPIO 2 (Physical Pin 3) Builtin Resistor
MANUAL_FILL_BUTTON_LED = 11  # The LED in the button is connected to GPIO 11 (Physical Pin 23)
POOL_FILL_RELAY = 17  # Our relay for the sprinkler valve is on GPIO 17 (Physical Pin 11)
POOL_FILL_TRANSFORMER_RELAY = 26 # Relay that controls power to the transformer that operates the sprinkler valve (Physical Pin 19)
SPRINKLER_RUN_LED = 5
PUMP_RUN_LED = 13
SYSTEM_RUN_LED = 21
SYSTEM_ERROR_LED = 16
POOL_FILLING_LED = 12
POOL_FILL_VALVE_DISABLED = 3
POOL_FILL_VALVE_DISABLED_LED = 4

global RUN_AS_DAEMON

## Are we in DEBUG mode? If so, do not run as a systemctl DAEMON. This disables watchdog support.
def check_debug_mode():
    if DEBUG == 1:
        print("Starting check_debug_mode()")
    global RUN_AS_DAEMON
    if DEBUG == 1:
        RUN_AS_DAEMON = False  # Watchdog setup - set to False to run from the command line for debugging.
    else:
        RUN_AS_DAEMON = True
    if DEBUG == 1:
        print("Completed check_debug_mode()")    

sock_rpt = True  # Used to report only the first socket message

def init():
    if DEBUG == 1:
        print("Starting init().")
    global RUN_AS_DAEMON
    # get the watchdog timeout period set in the systemd service file
    if RUN_AS_DAEMON == True:  # this will only work if started by systemd
        wd_usec = os.environ.get('WATCHDOG_USEC', None)
        if wd_usec == None or wd_usec == 0:
            logger.error("Pool Fill Control Terminating : incorrect watchdog interval sequence.")
            if DEBUG == 1:
                   print("Pool Fill Control Terminating : incorrect watchdog interval sequence.")
            exit(1)
    else:  # used when invoked by the shell
        wd_usec = 20000000  # 20 seconds

    wd_usec = int(wd_usec)
    # use half the time-out value in seconds for the watchdog ping routine to
    # account for Linux housekeeping chores
    wd_ping = wd_usec / 1000000 / 2
    

    try:
        ## Set up all of our GPIO Stuff here
        GPIO.setwarnings(False)  # Don't tell me about GPIO warnings.
        GPIO.setmode(GPIO.BCM)  # Use BCM Pin Numbering Scheme

        ## Setup our GPIO Pins
        GPIO.setup(POOL_FILL_RELAY, GPIO.OUT)
        GPIO.output(POOL_FILL_RELAY, True)  # Set inital state of our relay to off
	GPIO.setup(POOL_FILL_TRANSFORMER_RELAY, GPIO.OUT)
	GPIO.output(POOL_FILL_TRANSFORMER_RELAY, True) # Set initila state of our relay to off

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
        GPIO.setup(POOL_FILL_VALVE_DISABLED, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(POOL_FILL_VALVE_DISABLED_LED, GPIO.OUT)
        GPIO.output(POOL_FILL_VALVE_DISABLED_LED, False)

        # Setup our event detection for our manual fill button as well as our fill valve disable switch
        GPIO.add_event_detect(MANUAL_FILL_BUTTON, GPIO.RISING, callback=manual_fill_pool, bouncetime=1500)
        #GPIO.add_event_detect(POOL_FILL_VALVE_DISABLED, GPIO.BOTH, callback=is_pool_fill_valve_disabled, bouncetime=500)

        # notify systemd that we've finished the initialization
        retval = sd_notify(0, "READY=1")
        # check for a fatal error
        if retval <> 0:
            logger.error("Fatal sd_notify() error for script start".format(retval))
            if DEBUG == 1:
                print("Fatal sd_notify() error for script start".format(retval))
            os._exit(1)  # force the exit to the OS

        # start the first ping to the systemd sw watchdog and check for errors
        retval = sd_notify(0, "WATCHDOG=1")
        if retval <> 0:
            logger.error("Fatal sd_notify() error for watchdog ping, retval={0}".format(retval))
            if DEBUG == 1:
                print("Fatal sd_notify() error for watchdog ping".format(retval))
            os._exit(1)  # force the exit to the OS

    except Exception as e:
        logger.error("Exception in init()! DIE".format(e))
        if DEBUG == 1:
            print("Exception in init()! DIE DIE DIE".format(e))
        os._exit(1)  # force the exit to the OS
    
    if DEBUG == 1:
        print("Completed init().")


def sd_notify(unset_environment, s_cmd):
    if DEBUG == 1:
        print("Started sd_notify().")
    global sock_rpt
    sock = None
    if not RUN_AS_DAEMON:
        print ("Not running as a daemon, cannot communicate with systemd socket")
        return 0

    try:
        if not s_cmd:
            logger.error("Pool Fill Error : missing command to send.")
            if DEBUG == 1:
                print("Watchdog Setup Error. Missing command to send to sd_notify()")
            return 1

        s_adr = os.environ.get('NOTIFY_SOCKET', None)
        if sock_rpt:  # report this only one time
            logger.info("Notify socket = {0}".format(str(s_adr)))
            # this will normally return : /run/systemd/notify
            sock_rpt = False

        if not s_adr:
            logger.error("Error, missing socket.")
            if DEBUG == 1:
                print("Error, Missing socket.")
            return 1

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.sendto(s_cmd, s_adr)
        # sendto() returns number of bytes send
        if sock.sendto(s_cmd, s_adr) == 0:
            logger.error("Error, incorrect sock.sendto return value")
            if DEBUG == 1:
                print("ERROR: Incorrect sock.sendto return value!")
            return 1

    except exception as e:
        logger.error("Unexpecgted Exception in sd_notify".format(e))
        if DEBUG == 1:
            print("Unexpecgted Exception in sd_notify".format(e))
        os._exit(1)  # force the exit to the OS

    finally:
        # terminate the socket connection
        if sock:
            sock.close()
        if unset_environment:
            if 'NOTIFY_SOCKET' in os.environ:
                del os.environ['NOTIFY_SOCKET']
    return 0  # so we can test the return value for a successful execution

    if DEBUG == 1:
        print("Completed sd_notify().")


##Setup our Serial so we can communicate with our Moteino MightyHat LCD Sceen
def mightyhat_serial_setup():
    if DEBUG == 1:
        print("Starting mightyhat_serial_setup()")
    global ser
    ser = serial.Serial(
        port='/dev/ttyAMA0',
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1)
    logger.debug("MightyHat Serial setup completed.")
    if DEBUG == 1:
       print("MightyHat Serial setup completed")  

## Let's make LED Management a little easier!
# Blinking
def blink_led(pin, numTimes, speed):
    for i in range(0, numTimes):
        GPIO.output(pin, True)
        time.sleep(speed)
        GPIO.output(pin, False)
        time.sleep(speed)


# LED Control - ON/OFF
def led_control(led, onoff):
    if onoff == "ON":
        GPIO.output(led, True)
    elif onoff == "OFF":
        GPIO.output(led, False)


# Pool_Fill_Valve controls pool sprinkler relay as well as pool sprinkler transformer relay.
def pool_fill_valve(openclose):
    if openclose  == "OPEN":
         logger.info('pool_fill_valve called with OPEN command')
         GPIO.output(POOL_FILL_TRANSFORMER_RELAY, False) # Turns on the Sprinkler Transformer
         if DEBUG == 1:
             print("pool_fill_valve called with OPEN command")
             print("POOL_FILL_TRANSFORMER_RELAY is now powered and pool transformer is now ACTIVE")
         GPIO.output(POOL_FILL_RELAY, False)  # Turns on the sprinkler valve 
         if DEBUG == 1:
             print("POOL_FILL_RELAY is now powered and sprinkler valve solenoid is powered")
             print("Both relays should now be active and Sprinkler valve should be open and water should be running")
    elif openclose == "CLOSE":
         logger.info('pool_fill_valve called with CLOSE command')
         GPIO.output(POOL_FILL_RELAY, True)  # Turns off the sprinkler valve 
         if DEBUG == 1:
             print("pool_fill_valve called with CLOSE command")
             print("POOL_FILL_RELAY is now powered OFF and sprinkler valve solenoid is no longer powered")
         GPIO.output(POOL_FILL_TRANSFORMER_RELAY, True) # Turns off the Sprinkler Transformer
         if DEBUG == 1:
             print("POOL_FILL_TRANSFORMER_RELAY is now powered off and pool transformer is now OFF")
             print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")



# Here is where we check to see if our pool level sensor and pool temperature sensors are working correctly
# and their batteries are ok. We also track how many times ther sensors time out.

def max_pool_level_sensor_timeouts():
    if DEBUG == 1:
        print("Starting max_pool_level_sensor_timeouts()")
    global max_pool_level_sensor_timeouts_exceeded
    global current_pool_level_sensor_timeouts
    global pool_level_sensor_timeout_alert_sent
    current_pool_level_sensor_timeouts += 1
    logger.debug('Current pool level sensor timeouts are %s', current_pool_level_sensor_timeouts)
    if DEBUG == 1:
        print("Current pool level sensor timeouts are %s" % current_pool_level_sensor_timeouts)

    if current_pool_level_sensor_timeouts >= pooldb.max_pool_level_sensor_timeouts:
        logger.error('Pool Level Sensor Timeouts exceeded! Check for errors and restart program')
        if DEBUG == 1:
            print("Pool Level Sensor Timeouts exceeded! Check for errors and restart program")
        max_pool_level_sensor_timeouts_exceeded = "Yes"
        if pooldb.PoolAlerting == "True":
            send_notification('POOL_LEVEL_SENSOR_MAX_TIMEOUTS')
            if DEBUG == 1:
                print("POOL_LEVEL_SENSOR_MAX_TIMEOUTS Notifications Sent")
            pool_level_sensor_timeout_alert_sent = "Yes"
    if DEBUG == 1:
        print("Completed max_pool_level_sensor_timeouts()")



## This system relys on various sensors external to the RPi where this program runs. These sensors are
## important to the proper operation of this script. Currently the two sensors that are checked are the
## pool temperature (needed for accurace pH measurements) and the pool level which is required to monitor
## the water level. Since we start filling the pool when the pool level sensor says we are low, and then 
## we stop filling the pool when it says we are OK, it is important that this sensor is active. We check
## when the last time we have seen the sensor as well as it's battery level. If we lose communication with
## the sensor for three cycles, we deem it offline and immediately stop filling the pool as well as send
## an alert if you have pool alerting turned on. If the batteries are getting low in either sensor, we
## also send a notification.  

def check_pool_sensors():
    current_timestamp = int(time.time())
    logger.info('check_pool_sensors Current unix datetime stamp is: %s' % current_timestamp)
    if DEBUG == 1:
        print ("Current unix datetime stamp is: %s" % current_timestamp)

    try:
        cnx = mysql.connector.connect(user=pooldb.username, password=pooldb.password, host=pooldb.servername,
                                          database=pooldb.emoncms_db)
    except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error('Database connection failure: Check your username and password')
                if DEBUG == 1:
                    print("Database connection failure: Check your username and password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                logger.error('Database does not exist. Please check your settings.')
                if DEBUG == 1:
                    print("Database does not exist. Please check your settings.")
            else:
                logger.error('Unknown database error, please check all of your settings.')
                if DEBUG == 1:
                    print("Unknown database error, please check all of your settings.")
    else:
            cursor = cnx.cursor(buffered=True)
            cursor.execute(("SELECT time FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pool_level_table))

            for (data) in cursor:
                get_pool_level_sensor_time = int("%1.0f" % data)
                cursor.close()
                if DEBUG == 1:
                    print("Pool LEVEL sensor last updated at: %s" % get_pool_level_sensor_time)

            cursor = cnx.cursor(buffered=True)
            cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pool_level_sensor_battery_table))

            for (data) in cursor:
                get_pool_level_sensor_battery_voltage = float("%1.2f" % data)
                cursor.close()
                logger.info("Pool LEVEL sensor battery voltage is: %s" % get_pool_level_sensor_battery_voltage)
                if DEBUG ==1:
                    print("Pool LEVEL sensor battery voltage is: %s" % get_pool_level_sensor_battery_voltage)

            cursor = cnx.cursor(buffered=True)
            cursor.execute(("SELECT time FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pool_temp_table))

            for (data) in cursor:
                get_pool_temp_sensor_time = int("%1.0f" % data)
                cursor.close()
                if DEBUG == 1:
                    print("Pool TEMP sensor last updated at: %s" % get_pool_temp_sensor_time)

            cursor = cnx.cursor(buffered=True)
            cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pool_temp_sensor_battery_table))

            for (data) in cursor:
                get_pool_temp_sensor_battery_voltage = float("%1.2f" % data)
                cursor.close()
                logger.info("Pool TEMP sensor battery voltage is: %s" % get_pool_temp_sensor_battery_voltage)
                if DEBUG ==1:
                    print("Pool TEMP sensor battery voltage is: %s" % get_pool_temp_sensor_battery_voltage)

    cnx.close()

    pool_level_sensor_time_delta = current_timestamp - get_pool_level_sensor_time
    pool_temp_sensor_time_delta = current_timestamp - get_pool_temp_sensor_time

    logger.info("Time dfference between last pool LEVEL sensor reading is: %s seconds." % pool_level_sensor_time_delta)
    logger.info("Time dfference between last pool TEMP sensor reading is: %s seconds." % pool_temp_sensor_time_delta)
    if DEBUG == 1:
        print ("Time dfference between last pool LEVEL sensor reading is: %s seconds." % pool_level_sensor_time_delta)
        print ("Time dfference between last pool TEMP sensor reading is: %s seconds." % pool_temp_sensor_time_delta)

    if pool_level_sensor_time_delta > pooldb.max_pool_level_sensor_time_delta:
       logger.error("Pool Level Sensor TIMEOUT")
       if DEBUG ==1:
           print ("* * * * WARNING * * * *")
           print ("Pool LEVEL Sensor Timeout!")
       max_pool_level_sensor_timeouts()
    elif get_pool_level_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
       logger.error("Pool Level Sensor BATTERY voltage LOW")
       if DEBUG ==1:
           print ("* * * * WARNING * * * *")
           print ("Pool LEVEL Sensor Battery Voltage LOW!")
       if pooldb.PoolAlerting == "True":
           send_notification("POOL_LEVEL_SENSOR_BATTERY_LOW")
    elif pool_temp_sensor_time_delta > pooldb.max_pool_temp_sensor_time_delta:
       logger.error("Pool Temperature Sensor TIMEOUT")
       if DEBUG ==1:
           print ("* * * * WARNING * * * *")
           print ("Pool TEMP Sensor Timeout!")
    elif get_pool_temp_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
       logger.error("Pool Temperature Sensor BATTERY voltage LOW")
       if DEBUG ==1:
           print ("* * * * WARNING * * * *")
           print ("Pool TEMP Sensor Battery Voltage LOW!")
       if pooldb.PoolAlerting == "True":
           send_notification("POOL_TEMP_SENSOR_BATTERY_LOW")
    else:
       logger.info("Everything appears to be OK with the pool sensors!")
       if DEBUG ==1:
           print ("Everything appears to be OK with the pool sensors!")


## This function logs into our MySQL database gets the current resistance level for our liquid
## water level sensor mounted in our pool. This then matches that resistence level to min and
## max levels in pooldb.py and returns LOW or OK depending on the readings. This is called by
## pool_level() 

def get_pool_level_resistance():
    try:
        cnx = mysql.connector.connect(user=pooldb.username, password=pooldb.password, host=pooldb.servername,
                                          database=pooldb.emoncms_db)
    except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error('Database connection failure: Check your username and password')
                if DEBUG == 1:
                    print("Database connection failure: Check your username and password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                logger.error('Database does not exist. Please check your settings.')
                if DEBUG == 1:
                    print("Database does not exist. Please check your settings.")
            else:
                logger.error('Unknown database error, please check all of your settings.')
                if DEBUG == 1:
                    print("Unknown database error, please check all of your settings.")
    else:   
            cursor = cnx.cursor(buffered=True)
            cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pool_resistance_table))

            for (data) in cursor:
                get_pool_resistance = int("%1.0f" % data)
                cursor.close()
                if DEBUG == 1:
                    print("Pool Resistance is: %s" % get_pool_resistance)

    if get_pool_resistance >= pooldb.pool_resistance_critical_level:
        pool_level = "LOW"
        logger.info('get_pool_resistance() returned pool_level = LOW')
        if DEBUG == 1:
            print ("get_pool_level_resistance() returned pool_level = LOW")
    elif get_pool_resistance <= pooldb.pool_resistance_ok_level:
        pool_level = "OK"
        logger.info('get_pool_resistance() returned pool_level = OK')
        if DEBUG == 1:
            print ("get_pool_level_resistance() returned pool_level = OK")

    return pool_level



# Let's reach out and get our current pH and ORP, once we have the values,
# send them to one or more emoncms servers for logging.

## If we have a pH Probe installed (Atlas Scientific USB) set it up here
def ph_reading_setup():
    usbport1 = '/dev/PH'
    ph = serial.Serial(usbport1, pooldb.ph_probe_baud, timeout=0)
    # Turn off RESPONSES from the USB probe. We do not need them....
    ph.write("RESPONSE,0\r")
    # Turn off streaming from the probe. We will request the pH when
    # needed each time.
    ph.write("C,0\r")
    if DEBUG == 1:
        print("ph_reading_setup Completed.")

## This is part of the temperature compensation for the Atlas Scientific pH probe. If you have
## a pool water temp probe with values written to a mysql DB, you can set it up here.  
def get_pool_temp():
    if DEBUG == 1:
        print("Started get_pool_temp()")
    try:
       cnx = mysql.connector.connect(user=pooldb.username, password=pooldb.password, host=pooldb.servername,
             database=pooldb.emoncms_db)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
              logger.error('Database connection failure: Check your username and password')
              if DEBUG == 1:
                  print("Database connection failure: Check your username and password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
              logger.error('Database does not exist. Please check your settings.')
              if DEBUG == 1:
                  print("Database does not exist. Please check your settings.")
        else:
              logger.error('Unknown database error, please check all of your settings.')
              if DEBUG == 1:
                  print("Unknown database error, please check all of your settings.")
    else:
       cursor = cnx.cursor(buffered=True)
       cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.temp_probe_table))

       for (data) in cursor:
           get_pool_temp = float("%.2f" % data)
           cursor.close()
           logger.debug('get_pool_temp returned %.2fF', get_pool_temp)
           if DEBUG == 1:
               print("get_pool_temp returned %.2fF" % get_pool_temp)
       
       cnx.close()
       pool_temp = float((get_pool_temp - 32) / 1.8)
       if DEBUG == 1:
            print("pool_temp in C is %.2f" % pool_temp)

    return pool_temp

    if DEBUG == 1:
        print("Completed get_pool_temp()")    


## This is where we check to see if our pool pump is runing

def is_pool_pump_running():
    if DEBUG == 1:
        print("Started is_pool_pump_running()")
    try:
       cnx = mysql.connector.connect(user=pooldb.username, password=pooldb.password, host=pooldb.servername,
             database=pooldb.emoncms_db)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
              logger.error('Database connection failure: Check your username and password')
              if DEBUG == 1:
                  print("Database connection failure: Check your username and password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
              logger.error('Database does not exist. Please check your settings.')
              if DEBUG == 1:
                  print("Database does not exist. Please check your settings.")
        else:
              logger.error('Unknown database error, please check all of your settings.')
              if DEBUG == 1:
                  print("Unknown database error, please check all of your settings.")
    else:
       cursor = cnx.cursor(buffered=True)
       cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pump_running_watts_table))

       for (data) in cursor:
           pool_pump_running_watts = int("%1.0f" % data)
           cursor.close()
           logger.debug('pool_pump_running_watts returned %s watts in use by pump.', pool_pump_running_watts)
           if DEBUG == 1:
               print("pool_pump_running_watts returned %s watts in use by pump." % pool_pump_running_watts)

       if pool_pump_running_watts > pooldb.max_wattage:
             led_control(PUMP_RUN_LED, "ON")
             is_pool_pump_running = "Yes"
             logger.debug('PUMP_RUN_LED should be ON. This is the YELLOW LED')
             if DEBUG == 1:
                 print("PUMP_RUN_LED should be ON. This is the YELLOW LED")
       else:
             led_control(PUMP_RUN_LED, "OFF")
             is_pool_pump_running = "No"
             logger.debug('PUMP_RUN_LED should be OFF. This is the YELLOW LED')
             if DEBUG == 1:
                 print("PUMP_RUN_LED should be OFF. This is the YELLOW LED")

    return is_pool_pump_running




## Here is where we get our pH reading if we have a probe installed. 
## TODO: Only call or update pH when pool pump is running, otherwise
## pH will be inaccurate!

def get_ph_reading():
    if DEBUG == 1:
        print("Starting get_ph_reading().")
    usbport1 = '/dev/PH'
    ph = serial.Serial(usbport1, pooldb.ph_probe_baud, timeout=0)
    if pooldb.temp_probe == "Yes":
        pool_temp = get_pool_temp()
        # The pH Probe from Atlas has to be temperature compensated.
        # Here is where we send the latest temperature to the probe.
        ph.write("T,%d\r" % pool_temp)
        if DEBUG == 1:
            print("get_ph_reading get_pool_temp() returned %.2fC" % pool_temp)
            print("pH probe updated with new temperature %.2fC" % pool_temp)
    line = ""
    count = 1
    while (count < 2):
        ph.write("R\r")
        data = ph.read()
        if (data == "\r"):
            ph_value = str(line)
            logger.info("Current PH Reading is %s" % ph_value)
            if DEBUG == 1:
                print("Current PH Reading is %s" % ph_value)
            line = ""
            count = count + 1
        else:
            line = line + data

    if pooldb.emoncms_server1 == "Yes":
        res = requests.get("http://" + pooldb.server1 + "/" + pooldb.emoncmspath1 + "/input/post.json?&node=" + str(
            pooldb.ph_node) + "&csv=" + ph_value + "&apikey=" + pooldb.apikey1)
        logger.debug("Sent current PH Value: %s to Emoncms Server 1", ph_value)
        if DEBUG == 1:
            print("Sent current PH Value: "+ ph_value +" to Emoncms Server 1")
    if pooldb.emoncms_server2 == "Yes":
        res = requests.get("http://" + pooldb.server2 + "/" + pooldb.emoncmspath2 + "/input/post.json?&node=" + str(
            pooldb.ph_node) + "&csv=" + ph_value + "&apikey=" + pooldb.apikey2)
        logger.debug("Sent current PH Value: %s to Emoncms Server 2", ph_value)
        if DEBUG == 1:
            print("Sent current PH Value: "+ ph_value +" to Emoncms Server 2")

    if DEBUG == 1:
        print("Completed get_ph_reading()")


## If we have an ORP Probe installed (Atlas Scientific USB) set it up here
## TODO: Only call or update orp when pool pump is running, otherwise
## orp will be inaccurate!

def orp_reading_setup():
    usbport2 = '/dev/ORP'
    opr = serial.Serial(usbport2, pooldb.orp_probe_baud, timeout=0)
    if DEBUG == 1:
        print("orp_reading_setup Completed.")

def get_orp_reading():
    if DEBUG == 1:
        print("Starting get_orp_reading().")
    line2 = ""
    count = 1
    while (count < 2):
        data = orp.read()
        if (data == "\r"):
            orp_value = str(line2)
            logger.info("Current ORP Reading is %s" % orp_value)
            if DEBUG == 1:
                print("Current ORP Reading is %s" % orp_value)
            line2 = ""
            count = count + 1
        else:
            line2 = line2 + data

    if pooldb.emoncms_server1 == "Yes":
        res = requests.get("http://" + pooldb.server1 + "/" + pooldb.emoncmspath1 + "/input/post.json?&node=" + str(
            pooldb.orp_node) + "&csv=" + orp_value + "&apikey=" + pooldb.apikey1)
        logger.debug("Sent current ORP Value: %s to Emoncms Server 1", orp_value)
        if DEBUG == 1:
            print("Sent current ORP Value: "+ orp_value + " to Emoncms Server 1")
    if pooldb.emoncms_server2 == "Yes":
        res = requests.get("http://" + pooldb.server2 + "/" + pooldb.emoncmspath2 + "/input/post.json?&node=" + str(
            pooldb.orp_node) + "&csv=" + orp_value + "&apikey=" + pooldb.apikey2)
        logger.debug("Sent current ORP Value: %s to Emoncms Server 2", orp_value)
        if DEBUG == 1:
            print("Sent current ORP Value: "+ orp_value + " to Emoncms Server 2")

    if DEBUG == 1:
        print("Completed get_orp_reading()")


# This is where we set up our notifications. I use Pushbullet which is free and very powerful. Visit http://www.pushbullet.com for a free account.
# Once you have your free account, enter your API information in the pooldb.py file and restart the script.
pb = Pushbullet(pooldb.pushbilletAPI)

def send_notification(status):
    if DEBUG == 1:
        print("Started send_notification().")
    global alertsent
    global overfill_alert_sent
    global pool_fill_valve_alert_sent
    global pool_level_sensor_alert_sent
    global pool_level_sensor_batt_low_alert_sent
    global pool_level_sensor_timeout_alert_sent
    
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
    elif status == "POOL_LEVEL_SENSOR_TIMEOUT" and pool_level_sensor_alert_sent == "No":
        push = pb.push_note("Pool Level Sensor Timeout- ALERT",
                            "Your pool level sensor has timed out!")
        logger.error('Pushbullet Notification Sent - Pool Level Sensor Timeout')
        pool_level_sensor_alert_sent == "Yes"
    elif status == "POOL_LEVEL_SENSOR_BATTERY_LOW" and pool_level_sensor_batt_low_alert_sent == "No":
        push = pb.push_note("Pool Level Sensor Battery - ALERT",
                            "Your pool level sensor has a low battery!")
        logger.error('Pushbullet Notification Sent - Pool Level Sensor Timeout')
        pool_level_sensor_batt_low_alert_sent == "Yes"
    elif status == "POOL_TEMP_SENSOR_TIMEOUT" and pool_temp_sensor_alert_sent == "No":
        push = pb.push_note("Pool Temp Sensor Timeout- ALERT",
                            "Your pool temp sensor has timed out!")
        logger.error('Pushbullet Notification Sent - Pool Temp Sensor Timeout')
        pool_temp_sensor_alert_sent == "Yes"
    elif status == "POOL_TEMP_SENSOR_BATTERY_LOW" and pool_temp_sensor_batt_low_alert_sent == "No":
        push = pb.push_note("Pool Temp Sensor Battery - ALERT",
                            "Your pool temp sensor has a low battery!")
        logger.error('Pushbullet Notification Sent - Pool Temp Sensor Timeout')
        pool_temp_sensor_batt_low_alert_sent == "Yes"
    elif status == "POOL_LEVEL_SENSOR_MAX_TIMEOUTS" and pool_level_sensor_timeout_alert_sent == "No":
        push = pb.push_note("Pool Level Sensor Maximum Timeouts - ALERT",
                            "Your pool level sensor has timed out too many times!")
        logger.error('Pushbullet Notification Sent - Pool Level Sensor maximim Timeouts')
        pool_level_sensor_timeout_alert_sent == "Yes"


def start_ok():
    if DEBUG == 1:
        print("Starting start_ok()")
    ## Go ahead and send a notification that we started OK!
    if pooldb.PoolAlerting == "True":
        send_notification('STARTUP_OK')
    ## If we have a MightyHat with an LCD screen, we can output a message there as well....
    if pooldb.MightyHat == "True":
        ser.write('PFC_START_OK')
    ## Log startup
    logger.info('pool_fill_control.py %s started', VERSION)
    if DEBUG == 1:
        print("start_ok() completed")


def pfv_disabled():
    if DEBUG == 1:
        print("Starting pfv_disabled().")
    ## Let take a quick look at the switch that controls our fill valve. Has it been disabled? If so, send a notification
    ## and log the error.
    global pool_fill_valve_disabled
    pool_fill_valve_disabled = GPIO.input(POOL_FILL_VALVE_DISABLED)
    if pool_fill_valve_disabled == True:
        logger.error(
            'Pool Fill Valve has been DISABLED. System is OFFLINE. Reenable Pool Fill Valve to fill your pool!')
        led_control(POOL_FILL_VALVE_DISABLED_LED, "ON")
        logger.debug("POOL_FILL_VALVE_DISABLED_LED should be ON. This is a RED LED.")
        if pooldb.PoolAlerting == "True":
            send_notification('POOL_FILL_VALVE_DISABLED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_MANUALLY_DISABLED')
    if DEBUG == 1:
        print("Completed pfv_disabled() function")



# I use this to keep the pool from filling while my sprinklers are running. You could also use this as a means of
# creating a 'blackout' period during which time you do not want your pool filled.
# This is the sprinkler start and stop times. Python is a bit weird in that you cannot use 0900 or 0800 because
# of the leading '0'. Any other time is ok.
# Use military time but DO NOT use leading zeros!

def get_sprinkler_status():
    if DEBUG == 1:
        print("Started get_sprinkler_status().")
    if pooldb.sprinkler_type == "Timer":
        SprinklerStart = int(400)
        SprinklerStop = int(1000)

        current_military_time = int(datetime.datetime.now().strftime('%H%M'))
        logger.debug('Current military time is being reported as %s.', current_military_time)

        if SprinklerStart < current_military_time < SprinklerStop:
            sprinklers_on = "Yes"
            logger.debug('Sprinklers running. (TIMER)')
            if DEBUG == 1:
                print("Sprinklers running (TIMER)")
            led_control(SPRINKLER_RUN_LED, "ON")
            logger.debug('SPRINKLER_RUN_LED should be ON. This is a BLUE LED')
            if DEBUG == 1:
                print("SPRINKLER_RUN_LED should be ON. This is a BLUE LED")
        else:
            sprinklers_on = "No"
            logger.debug('Sprinklers are not running (TIMER).')
            if DEBUG == 1:
                print("Sprinklers are not running (TIMER)")
            led_control(SPRINKLER_RUN_LED, "OFF")
            logger.debug('SPRINKLER_RUN_LED should be OFF. This is a BLUE LED')
            if DEBUG == 1:
                print("SPRINKLER_RUN_LED should be OFF. This is a BLUE LED")

        return sprinklers_on

    else:
        if DEBUG == 1:
            print("subprocess call for sprinklers called.")
        output = subprocess.check_output(pooldb.rachio_url, shell=True)
        if output == "{}":
            sprinklers_on = "No"
            logger.debug('Sprinklers are not running (RACHIO).')
            if DEBUG == 1:
                print("Sprinklers are not running (RACHIO).")
            led_control(SPRINKLER_RUN_LED, "OFF")
            logger.debug('SPRINKLER_RUN_LED should be OFF. This is a BLUE LED')
            if DEBUG == 1:
                print("SPRINKLER_RUN_LED should be OFF. This is a BLUE LED")
        else:
            sprinklers_on = "Yes"
            logger.debug('Sprinklers running. (RACHIO)')
            if DEBUG == 1:
                print("Sprinklers running. (RACHIO)")
            led_control(SPRINKLER_RUN_LED, "ON")
            logger.debug('SPRINKLER_RUN_LED should be ON. This is a BLUE LED')
            if DEBUG == 1:
                print("SPRINKLER_RUN_LED should be ON. This is a BLUE LED")

        return sprinklers_on

    if DEBUG == 1:
        print("Completed get_sprinkler_status()")


# This turns the sprinkler valve on or off when called
def fill_pool_auto(fill_now):
    if DEBUG == 1:
        print("Starting fill_pool_auto() function")
    global pool_is_filling
    global current_run_time
    if fill_now == "START":
        pool_is_filling = "Auto"
        pool_fill_valve("OPEN")
        logger.info('Pool AUTOMATIC fill started.')
        if DEBUG == 1:
            print("Pool AUTOMATIC fill started.")
        led_control(POOL_FILLING_LED, "ON")
        logger.debug('POOL_FILLING_LED should be ON. This is a BLUE LED')
        if DEBUG == 1:
            print("POOL_FILLING_LED should be ON. This is a BLUE LED")
        if pooldb.MightyHat == "True":
            ser.write('PFC_AUTO_FILL')
            logger.debug('Pool Automatic Fill started (PFC_AUTO_FILL) sent to MightyHat')
            if DEBUG == 1:
                print("Pool Automatic Fill started (PFC_AUTO_FILL) sent to MightyHat")
        if pooldb.PoolAlerting == "True":
            send_notification('FILLING')
    elif fill_now == "STOP":
        pool_is_filling = "No"
        pool_fill_valve("CLOSE")
        logger.info('Pool AUTOMATIC fill completed.')
        if DEBUG == 1:
            print("Pool AUTOMATIC fill completed.")
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        if DEBUG == 1:
            print("POOL_FILLING_LED should be OFF. This is a BLUE LED")
        current_run_time = 0
        if pooldb.MightyHat == "True":
            ser.write('PFC_FILL_DONE')
            logger.debug('Pool filling complete (PFC_FILL_DONE) sent to MightyHat')
            if DEBUG == 1:
                print("Pool filling complete (PFC_FILL_DONE) sent to MightyHat")
        if pooldb.PoolAlerting == "True":
            send_notification('DONE_FILLING')
    elif fill_now == "FORCE_STOP":
        pool_is_filling = "No"
        pool_fill_valve("CLOSE")
        logger.warning('Pool AUTOMATIC fill FORCE STOPPED.')
        if DEBUG == 1:
            print("Pool AUTOMATIC fill FORCE STOPPED.")
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        if DEBUG == 1:
            print("POOL_FILLING_LED should be OFF. This is a BLUE LED")
        led_control(SYSTEM_ERROR_LED, "ON")
        logger.debug('SYSTEM_ERROR_LED should be ON. This is the RED LED')
        if DEBUG == 1:
            print("SYSTEM_ERROR_LED should be ON. This is the RED LED")
        if pooldb.MightyHat == "True":
            ser.write('PFC_OVERFILL')
            logger.debug('Pool Automatic Fill Force Stopped (PFC_OVERFILL) sent to MightyHat')
            if DEBUG == 1:
                print("Pool Automatic Fill Force Stopped (PFC_OVERFILL) sent to MightyHat")
    elif fill_now == "MANUAL_VALVE_DISABLED":
        pool_is_filling = "No"
        pool_fill_valve("CLOSE")
        logger.warning('Pool AUTOMATIC fill FORCE STOPPED - Fill Valve has been manually disabled.')
        if DEBUG == 1:
            print("Pool AUTOMATIC fill FORCE STOPPED - Fill Valve has been manually disabled.")
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        if DEBUG == 1:
            print("POOL_FILLING_LED should be OFF. This is a BLUE LED")
        led_control(SYSTEM_ERROR_LED, "ON")
        logger.debug('SYSTEM_ERROR_LED should be ON. This is the RED LED')
        if DEBUG == 1:
            print("SYSTEM_ERROR_LED should be ON. This is the RED LED")

    if DEBUG == 1:
        print("Completed fill_pool_auto() function")


# This turns the sprinkler valve on or off when manual button is pushed.
def fill_pool_manual(fill_now):
    logger.info('Started fill_pool_manual() function')
    if DEBUG == 1:
        print("Started fill_pool_manual() function")
    global pool_is_filling
    global current_run_time
    global MANUAL_FILL_BUTTON_LED_ON
    if fill_now == "START":
        pool_is_filling = "Manual"
        if DEBUG == 1:
            print("Manual fill control calling pool_fill_valve with OPEN command - Manual Fill Button Pushed")
        pool_fill_valve("OPEN")
        logger.info('Pool MANUAL fill started. pool_fill_valve = OPEN')
        if DEBUG == 1:
            print("Pool MANUAL fill started. pool_fill_valve = OPEN")
        if pooldb.MightyHat == "True":
            ser.write('PFC_MAN_FILL')
            logger.debug('Pool manual fill started (PFC_MAN_FILL) sent to MightyHat')
            if DEBUG == 1:
                print("Pool manual fill started (PFC_MAN_FILL) sent to MightyHat")
    elif fill_now == "STOP":
        pool_is_filling = "No"
        if DEBUG == 1:
            print("Manual fill control calling pool_fill_valve with CLOSE command - Manual Fill Button Pushed")
        pool_fill_valve("CLOSE")
        logger.info('Pool MANUAL fill completed. pool_fill_valve = CLOSE')
        if DEBUG == 1:
            print("Pool MANUAL fill completed. pool_fill_valve = CLOSE")
        current_run_time = 0
        if pooldb.MightyHat == "True":
            ser.write('PFC_FILL_DONE')
            logger.debug('Pool Fill Complete (PFC_FILL_DONE) sent to MightyHat')
            if DEBUG == 1:
                print("Pool Fill Complete (PFC_FILL_DONE) sent to MightyHat")
    elif fill_now == "MANUAL_VALVE_DISABLED":
        pool_is_filling = "No"
        if DEBUG == 1:
            print("Manual fill control calling pool_fill_valve with CLOSE command - Manual Valve Disabled")
        pool_fill_valve("CLOSE")
        led_control(MANUAL_FILL_BUTTON_LED, "OFF")
        MANUAL_FILL_BUTTON_LED_ON = False
        logger.warning('Pool MANUAL fill FORCE STOPPED - Fill Valve has been manually disabled.')
        if DEBUG == 1:
            print("Pool MANUAL fill FORCE STOPPED - Fill Valve has been manually disabled.")
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        if DEBUG == 1:
            print("POOL_FILLING_LED should be OFF. This is a BLUE LED")
        led_control(SYSTEM_ERROR_LED, "ON")
        logger.debug('SYSTEM_ERROR_LED should be ON. This is the RED LED')
        if DEBUG == 1:
            print("SYSTEM_ERROR_LED should be ON. This is the RED LED")
    
    logger.info('Completed fill_pool_manual() function')
    if DEBUG == 1:
        print("Completed fill_pool_manual() function")



# Called from the fill_pool() routine and keeps track of how many times we have checked the pool level. 
# We can then decide what to do if it is taking too long to fill the pool (or the sensor node died before
# it could update the database). In this case, it simply flags the max_run_time_exceeded variable, shuts off
# the water, logs the error and waits for you to restart the program which clears the variable. 
# The max run time is set in the pooldb.py file and is based more on run 'cycles' than run 'time'. For example
# if you set the checktime (in pooldb.py) to 120 seconds and maxruntime to 100, then it would be 100 * 120 seconds
# before the current_run_time would exceed max_run_time. So be careful!
def max_run_time():
    if DEBUG == 1:
        print("Starting max_run_time()")
    global max_run_time_exceeded
    global current_run_time
    global overfill_alert_sent
    current_run_time += 1
    logger.debug('Current fill run time is %s', current_run_time)
    if DEBUG == 1:
        print("Current fill run time is %s" % current_run_time)

    if current_run_time >= pooldb.maxruntime:
        logger.error('Pool Maxruntime exceeded! Check for errors and restart program')
        if DEBUG == 1:
            print("Pool Maxruntime exceeded! Check for errors and restart program")
        max_run_time_exceeded = "Yes"
        if pooldb.PoolAlerting == "True":
            send_notification('POOL_OVERFILL')
            if DEBUG == 1:
                print("POOL_OVERFILL Notifications Sent")
            overfill_alert_sent == "Yes"
    if DEBUG == 1:
        print("Completed max_run_time()")

    return max_run_time_exceeded



## This is the main function in the script. This checks a bunch of things (sprinklers, pool resistance level, etc)
## and then decides what to do about filling the pool. If the pool needs to be filled, it checks the level of the
## pool by calling the get_pool_level_resistance() function and also tracks how many cycles we have been filling
## the pool. Once the pool is full, it shuts off the water.
 
def pool_level():
    if DEBUG == 1:
        print("Starting pool_level()")
    global pool_pump_running_watts
    global pool_is_filling
    global max_run_time_exceeded
    global sprinkler_status
    global pool_fill_valve_disabled
    global max_pool_level_sensor_timeouts_exceeded
    pool_pump_running = is_pool_pump_running()
    sprinkler_status = get_sprinkler_status()
    get_pool_level = get_pool_level_resistance()
    check_pool_sensors()
    if pooldb.ph_probe == "Yes":
        get_ph_reading()
    if pooldb.orp_probe == "Yes":
        get_orp_reading()
    sd_notify(0,
              "WATCHDOG=1")  # Ping the watchdog once per check. It is set to restart the script if no notification within 70 seconds.
    logger.debug("Watchdog Ping Sent")
    if DEBUG == 1:
        print("Watchdog Ping Sent")
    if MANUAL_FILL_BUTTON_LED_ON == True or pool_fill_valve_disabled == True:  # Why bother checking if we are manually filling the pool....?
        if MANUAL_FILL_BUTTON_LED_ON == True:
            logger.debug("pool_level function BYPASSED, Manual fill is in progress.")
            if DEBUG == 1:
                print("pool_level function BYPASSED, Manual fill is in progress.")
        elif pool_fill_valve_disabled == True:
            logger.debug("pool_level function BYPASSED, pool fill valve has been manually disabled")
            if DEBUG == 1:
                print("pool_level function BYPASSED, pool fill valve has been manually disabled")
        pass
    else:
       if get_pool_level == "OK" and pooldb.MightyHat == "True":
           logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
           if DEBUG == 1:
               print("POOL_FILLING_LED should be OFF. This is a BLUE LED")
           ser.write('PFC_LEVEL_OK')
           logger.debug('Pool Level OK (PFC_LEVEL_OK) sent to MightyHat')
           if DEBUG == 1:
               print("Pool Level OK (PFC_LEVEL_OK) sent to MightyHat")

       if get_pool_level == "OK" and pool_is_filling == "Auto":
           fill_pool_auto('STOP')

       elif get_pool_level == "LOW":
           if pooldb.MightyHat == "True":
               ser.write('PFC_LEVEL_LOW')
               logger.debug('Pool Level Low (PFC_LEVEL_LOW) sent to MightyHat')
               if DEBUG == 1:
                   print("Pool Level Low (PFC_LEVEL_LOW) sent to MightyHat")
           sprinkler_status = get_sprinkler_status()
           if sprinkler_status == "Yes":
               logger.info('Sprinklers are running, we cannot fill the pool at this time.')
               if DEBUG == 1:
                   print("Sprinklers are running, we cannot fill the pool at this time.")
               if pooldb.MightyHat == "True":
                   ser.write('PFC_SPRINKLERS')
                   logger.debug('Sprinklers are running (PFC_SPRINKLERS) sent to MightyHat')
                   if DEBUG == 1:
                       print("Sprinklers are running (PFC_SPRINKLERS) sent to MightyHat")
               pass
           elif pool_pump_running == "Yes":
               logger.info('Pool pump is running, we cannot fill the pool at this time.')
               if DEBUG == 1:
                   print("Pool pump is running, we cannot fill the pool at this time.")
               if pooldb.MightyHat == "True":
                   ser.write('PFC_PUMP')
                   logger.debug('Pool pump is running (PFC_PUMP) sent to MightyHat')
                   if DEBUG == 1:
                       print("Pool pump is running (PFC_PUMP) sent to MightyHat")
               pass
           else:
               max_run_time()
               if max_run_time_exceeded == "Yes" or max_pool_level_sensor_timeouts_exceeded == "Yes":
                   fill_pool_auto('FORCE_STOP')
               elif pool_is_filling == "No":
                   fill_pool_auto('START')

    threading.Timer(pooldb.checktime, pool_level).start()


# This manages our manaul fill pushbutton
def manual_fill_pool(button):
    logger.info('Manual Fill Button Pushed - Starting manual_fill_pool() function')
    if DEBUG == 1:
        print ("Manual Fill Button Pushed - Starting manual_fill_pool() function")
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
        if DEBUG == 1:
            print("POOL_FILLING_LED should be ON. This is a BLUE LED")
        if pooldb.PoolAlerting == "True":
            send_notification('MANUAL_FILL')
    elif pool_is_filling == "Manual":
        GPIO.output(MANUAL_FILL_BUTTON_LED, False)
        MANUAL_FILL_BUTTON_LED_ON = False
        fill_pool_manual('STOP')
        led_control(POOL_FILLING_LED, "OFF")
        logger.debug('POOL_FILLING_LED should be OFF. This is a BLUE LED')
        if DEBUG == 1:
            print("POOL_FILLING_LED should be OFF. This is a BLUE LED")
        if pooldb.PoolAlerting == "True":
            send_notification('MANUAL_FILL_COMPLETE')
    else:
        blink_led(MANUAL_FILL_BUTTON_LED, 7, 0.1)
        if sprinkler_status == "Yes":
            logger.info("Manual fill attempted while sprinklers were running.")
            if DEBUG == 1:
                print("Manual fill attempted while sprinklers were running.")
        elif pool_pump_running_watts >= pooldb.max_wattage:
            logger.info("Manual fill attempted while pool pump was running.")
            if DEBUG == 1:
                print("Manual fill attempted while pool pump was running.")
        elif pool_is_filling == "Auto":
            logger.info("Manual fill attempted while pool was automatically filling.")
            if DEBUG == 1:
                print("Manual fill attempted while pool was automatically filling.")
        elif pool_fill_valve_disabled:
            logger.info("Manual fill attempted with pool valve manually disabled.")
            if DEBUG == 1:
                print("Manual fill attempted with pool valve manually disabled.")
        else:
            logger.info("Unspecified Manual Fill Error")
            if DEBUG == 1:
                print("Unspecified Manual Fill Error")
    if DEBUG == 1:
        print("Completed manual_fill_pool() function")


def is_pool_fill_valve_disabled(channel):
    if DEBUG == 1:
        print("Starting is_pool_fill_valve_disabled() function")
    global pool_fill_valve_disabled
    global pool_is_filling
    pool_fill_valve_disabled = GPIO.input(POOL_FILL_VALVE_DISABLED)
    if pool_fill_valve_disabled == True:
        if pool_is_filling == "Auto":
            fill_pool_auto('MANUAL_VALVE_DISABLED')
        else:
            fill_pool_manual('MANUAL_VALVE_DISABLED')
        logger.info("Manual pool fill valve has been DISABLED! Reenable to fill pool.")
        if DEBUG == 1:
            print("Manual pool fill valve has been DISABLED! Reenable to fill pool.")
        led_control(POOL_FILL_VALVE_DISABLED_LED, "ON")
        led_control(SYSTEM_ERROR_LED, "ON")
        logger.debug("POOL_FILL_VALVE_DISABLED_LED should be ON. This is a RED LED.")
        if DEBUG == 1:
            print("POOL_FILL_VALVE_DISABLED_LED should be ON. This is a RED LED.")
        logger.debug("SYSTEM_ERROR_LED should be ON. This is a RED LED.")
        if DEBUG == 1:
            print("SYSTEM_ERROR_LED should be ON. This is a RED LED.")
        if pooldb.PoolAlerting == "True":
            send_notification('POOL_FILL_VALVE_DISABLED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_MANUALLY_DISABLED')
    elif not (pool_fill_valve_disabled):
        led_control(POOL_FILL_VALVE_DISABLED_LED, "OFF")
        led_control(SYSTEM_ERROR_LED, "OFF")
        logger.debug("POOL_FILL_VALVE_DISABLED_LED should be OFF. This is a RED LED.")
        if DEBUG == 1:
            print("POOL_FILL_VALVE_DISABLED_LED should be OFF. This is a RED LED.")
        logger.debug("SYSTEM_ERROR_LED should be OFF. This is a RED LED.")
        if DEBUG == 1:
            print("SYSTEM_ERROR_LED should be OFF. This is a RED LED.")
        logger.info("Manual pool fill valve has been REENABLED.")
        if DEBUG == 1:
            print("Manual pool fill valve has been REENABLED.")
        pool_is_filling = "No"
        if pooldb.PoolAlerting == "True":
            send_notification('POOL_FILL_VALVE_REENABLED')
        if pooldb.MightyHat == "True":
            ser.write('PFC_MANUALLY_REENABLED')
        pool_level()

    if DEBUG == 1:
        print("Completed is_pool_fill_valve_disabled() function")



def main():
    if DEBUG == 1:
        print("Starting Main")
    check_debug_mode()
    init()
    if pooldb.ph_probe == "Yes":
        ph_reading_setup()
    if pooldb.orp_probe == "Yes":
        orp_reading_setup()
    if pooldb.MightyHat == "True":
        mightyhat_serial_setup()
    start_ok()
    pfv_disabled()
    led_control(SYSTEM_RUN_LED, "ON")
    if DEBUG == 1:
        print("System Run LED has been turned on.")
    if DEBUG == 1:
        print("Staring initial call to pool_level().")
    pool_level()


if __name__ == '__main__':
    main()

