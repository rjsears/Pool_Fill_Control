#!/usr/bin/python
""" Python script to  check pool temp,level,acid level and filter PSI  """

# Can be run manually or via cron
__author__ = 'Richard J. Sears'
VERSION = "V3.3.02 (2018-02-09)"
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


config = ConfigParser.ConfigParser()
current_timestamp = int(time.time())


# You can use pooldb.DEBUG here or you can set DEBUG = True or 
# DEBUG = False. Assuming that you are running this from a cron,
# you can set your cron job to dump output to /dev/null by adding:
# "  > /dev/null 2>&1  " to the end of the cron job. In doing so, you
# can run DEBUG = True here or in pooldb and when you manually run
# this from the command line it will output all of your information
# but from a cron it will not.
DEBUG = pooldb.DEBUG
LOGGING = pooldb.LOGGING
EMAIL = pooldb.EMAIL
PUSHBULLET = pooldb.PUSHBULLET
alert_email = pooldb.alert_email

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

#########################################
# Set up Logging
#########################################
if LOGGING:
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


# We use Push Bullet to send out all of our alerts
def send_push_notification(title, message):
    pb = Pushbullet(pooldb.pushbilletAPI)
    push = pb.push_note(title, message)



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
    if DEBUG:
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


def get_sprinkler_status():
    """ Function to determine if our sprinklers are currently running. """
    if DEBUG:
        print("Started get_sprinkler_status().")
    if pooldb.sprinkler_type == "Timer":
        SprinklerStart = int(400)
        SprinklerStop = int(1000)

        current_military_time = int(datetime.datetime.now().strftime('%H%M'))

        if SprinklerStart < current_military_time < SprinklerStop:
            sprinklers_on = "True"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", True)
            if DEBUG:
                print("Sprinklers running (TIMER)")
            led_control(sprinkler_run_led, "True")
            if DEBUG:
                print("SPRINKLER_RUN_LED should be ON. This is a BLUE LED")
        else:
            sprinklers_on = "False"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", False)
            if DEBUG:
                print("Sprinklers are not running (TIMER)")
            led_control(sprinkler_run_led, "False")
            if DEBUG:
                print("SPRINKLER_RUN_LED should be OFF. This is a BLUE LED")
        return sprinklers_on
    else:
        if DEBUG:
            print("subprocess call for sprinklers called.")
        output = subprocess.check_output(pooldb.rachio_url, shell=True)
        if output == "{}":
            sprinklers_on = "False"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", False)
            if DEBUG:
                print("Sprinklers are not running (RACHIO).")
            led_control(sprinkler_run_led, "False")
            if DEBUG:
                print("SPRINKLER_RUN_LED should be OFF. This is a BLUE LED")
        else:
            sprinklers_on = "True"
            update_pool_sensor_status_values("pool_sensor_status", "sprinkler_status", "sprinklers_on", True)
            if DEBUG:
                print("Sprinklers running. (RACHIO)")
            led_control(sprinkler_run_led, "True")
            if DEBUG:
                print("SPRINKLER_RUN_LED should be ON. This is a BLUE LED")
    if DEBUG:
        print("Completed get_sprinkler_status()")
    return sprinklers_on


# TODO - Complete this function, add notification via PB once until PFV reenabled!
def pfv_disabled():
    # TODO Complete and test pfv_disabled() function
    """ Function to determine if our PFV has been manually disabled. """
    if DEBUG:
        print("Starting pfv_disabled().")
    # Let take a quick look at the switch that controls our fill valve. Has
    # it been disabled? If so, send a notification
    # and log the error.
    pool_fill_valve_disabled = GPIO.input(pool_fill_valve_disabled_pin)
    if pool_fill_valve_disabled == True:
        led_control(pool_fill_valve_disabled_led, "True")
        send_push_notification("Pool Fill Valve DISABLED", "Your pool fill valve has been DISABLED. Pool will not fill.")
    if DEBUG:
        print("Completed pfv_disabled() function")

# Pool_Fill_Valve controls pool sprinkler relay as well as pool sprinkler
# transformer relay.
def pool_fill_valve(openclose):
    current_timestamp = int(time.time())
    if openclose == "OPEN":
       sprinkler_status = get_sprinkler_status()
       if sprinkler_status == "True":
           if DEBUG:
               print("Sprinklers are running, we cannot fill the pool at this time, we will try again later.")
           pass
       pool_level_sensor_ok = read_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok")
       if pool_level_sensor_ok == "False":
           if DEBUG:
               print("There is a problem with your pool level sensor and we cannot fill the pool.")
           pass
       update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", True)
       update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time", current_timestamp)
       GPIO.output(pool_fill_transformer_relay, True)  # Turns on the Sprinkler Transformer
       GPIO.output(pool_fill_relay, True)  # Turns on the sprinkler valve
       led_control(pool_filling_led, "True") # Turns on the pool filling blue LED
       update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", True)
       if LOGGING:
           logger.info("Pool is refilling.")
       if DEBUG:
           print("pool_fill_valve called with OPEN command")
           print("pool_fill_transformer_relay is now powered and pool transformer is now ACTIVE")
           print("pool_fill_relay is now powered and sprinkler valve solenoid is now powered.")
           print("Both relays should now be active and Sprinkler valve should be open and water should be running.")
           print("Pool Filling LED should be on. This is a BLUE LED")
       if PUSHBULLET:
           send_push_notification("Your Pool Is Filling", "Your swimming pool is refilling.")
       if EMAIL:
           send_email(pooldb.alert_email, 'Your Pool is Filling', 'Your Pool is low and is currently refilling.')
    elif openclose == "CLOSE":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        if LOGGING:
            logger.info("Pool is done refilling.")
        if DEBUG:
            print("pool_fill_valve called with CLOSE command")
            print("pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered.")
            print("pool_fill_transformer_relay is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")
        if PUSHBULLET:
            send_push_notification("Your Pool is Done Filling", "Your swimming pool is done refilling.")
        if EMAIL:
            send_email(pooldb.alert_email, 'Your Pool is Done Filling', 'Your pool is done refilling!')
    elif openclose == "WEBCLOSE":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        if LOGGING:
            logger.info("Auto Fill terminated by Web Request.")
        if DEBUG:
            print("pool_fill_valve called with WEBCLOSE command")
            print("pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered.")
            print("pool_fill_transformer_relay is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")
        if PUSHBULLET:
            send_push_notification("Pool Auto Fill terminated by Web Request", "Your swimming pool has stopped filling due to a Web request.")
        if EMAIL:
            send_email(pooldb.alert_email, 'Pool Auto Fill Terminated by Web Request', 'Your swimming pool has stopped filling due to a web request')
    elif openclose == "CRITICALCLOSE":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False")  # Turns off the pool filling blue LED
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        led_control(system_error_led, "True") # Turns on the System Error LED
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_error_led", True)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        if LOGGING:
            logger.warn("Pool Fill CRITICAL Stop!")
        if DEBUG:
            print("pool_fill_valve called with CRITICAL CLOSE command")
            print("pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered.")
            print("Pool filling LED should be off. This is a BLUE LED.")
            print("System Error LED should be on. This is a RED LED.")
            print("pool_fill_transformer_relay is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")
        if PUSHBULLET:
            send_push_notification("Pool Fill Stopped with CRITICAL CLOSE", "Your swimming pool fill was stopped by a CRITICAL CLOSE Command.")
        if EMAIL:
            send_email(pooldb.alert_email, 'Pool Fill - CRITICAL STOP!', 'You pool has stopped filling due to a CRITICAL STOP! Please check the system.')
    elif openclose == "RESET":
        GPIO.output(pool_fill_relay, False)  # Turns off the sprinkler valve
        GPIO.output(pool_fill_transformer_relay, False)  # Turns off the Sprinkler Transformer
        led_control(pool_filling_led, "False") # Turns off the pool filling blue LED
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        if DEBUG:
            print("pool_fill_valve called with RESET command")
        if LOGGING:
            logger.info("pool_fill_valve called with RESET command")
    elif openclose == "MANUAL_OPEN":
        sprinkler_status = get_sprinkler_status()
        if sprinkler_status == "True":
            blink_led(manual_fill_button_led, 7, 0.1)
            if DEBUG:
                print("Sprinklers are running, we cannot fill the pool at this time, we will try again later.")
            pass
        pool_level_sensor_ok = read_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok")
        if pool_level_sensor_ok == "False":
            blink_led(manual_fill_button_led, 7, 0.1)
            if DEBUG:
                print("There is a problem with your pool level sensor and we cannot fill the pool.")
            pass
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", True)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time", current_timestamp)
        GPIO.output(pool_fill_transformer_relay, True)  # Turns on the Sprinkler Transformer
        GPIO.output(pool_fill_relay, True)  # Turns on the sprinkler valve
        led_control(pool_filling_led, "True")  # Turns on the pool filling blue LED
        led_control(manual_fill_button_led, "True")
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", True)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "manual_fill_button_led", True)
        if PUSHBULLET:
            send_push_notification("Your Pool is MANUALLY Filling", "Your swimming pool is MANUALLY refilling.")
        if LOGGING:
            logger.info("Your Pool is MANUALLY Filling.")
        if EMAIL:
            send_email(pooldb.alert_email, 'Your pool is MANUALLY Filling', 'Your pool is being manually filled!')
        if DEBUG:
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
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pool_filling_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "manual_fill_button_led", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling", False)
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", 0)
        if LOGGING:
            logger.info("Your Pool is done MANUALLY Filling.")
        if DEBUG:
            print("MANUAL FILL BUTTON - pool_fill_valve called with CLOSE command")
            print("pool_fill_relay is now powered OFF and sprinkler valve solenoid is no longer powered.")
            print("pool_fill_transformer_relay is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")
        if PUSHBULLET:
            send_push_notification("Your Pool Is Done (MANUALLY) Filling", "Your swimming pool is done (MANUALLY) refilling.")
        if EMAIL:
            send_email(pooldb.alert_email, 'Your Pool is done MANUALLY Filling.', 'Your Pool is done MANUALLY Filling.')


def check_pool_sensors():
    if DEBUG:
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
        if DEBUG:
            print("Pool LEVEL sensor last updated at: %s" % get_pool_level_sensor_time)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_level_sensor_battery_table))

    for data in cursor:
        get_pool_level_sensor_battery_voltage = float("%1.2f" % data)
        cursor.close()
        get_battery_percentage(get_pool_level_sensor_battery_voltage)
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_level_batt_percentage", batt_level)
        if DEBUG:
            print("Pool LEVEL sensor battery voltage is: %s" % get_pool_level_sensor_battery_voltage)
            print ("Pool LEVEL sensor battery percentage  is %s" % batt_level)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT time FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_temp_table))

    for data in cursor:
        get_pool_temp_sensor_time = int("%1.0f" % data)
        cursor.close()
        if DEBUG:
            print("Pool TEMP sensor last updated at: %s" % get_pool_temp_sensor_time)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
        pooldb.pool_temp_sensor_battery_table))

    for data in cursor:
        get_pool_temp_sensor_battery_voltage = float("%1.2f" % data)
        cursor.close()
        get_battery_percentage(get_pool_temp_sensor_battery_voltage)
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_temp_batt_percentage", batt_level)
        if DEBUG:
            print("Pool TEMP sensor battery voltage is: %s" % get_pool_temp_sensor_battery_voltage)
            print ("Pool TEMP sensor battery percentage  is %s" % batt_level)

    cursor = cnx.cursor(buffered=True)
    cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (pooldb.pool_filter_psi_table))
    for data in cursor:
        get_pool_filter_psi = int("%1.0f" % data)
        cursor.close()
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "filter_current_psi", get_pool_filter_psi)
        if DEBUG:
            print("Pool FILTER PSI is: %s" % get_pool_filter_psi)

    cnx.close()

    pool_level_sensor_time_delta = current_timestamp - get_pool_level_sensor_time
    pool_temp_sensor_time_delta = current_timestamp - get_pool_temp_sensor_time

    pool_level_timeout_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent")
    pool_level_lowvoltage_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent")
    pool_temp_timeout_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent")
    pool_temp_lowvoltage_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status","pool_temp_low_voltage_alert_sent")
    pool_filter_high_psi_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status","pool_filter_psi_alert_sent")

    if DEBUG:
        print ("Time dfference between last pool LEVEL sensor reading is: %s "
            "seconds." % pool_level_sensor_time_delta)
        print ("Time dfference between last pool TEMP sensor reading is: %s "
            "seconds." % pool_temp_sensor_time_delta)

    if pool_level_sensor_time_delta > pooldb.max_pool_level_sensor_time_delta:
        if pool_level_timeout_alert_sent == "True":
            pass
        else:
            if PUSHBULLET:
                send_push_notification("Pool Level Sensor Timeout", "Your Pool Level Sensor has Timed Out!")
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", False)
            if LOGGING:
                logger.warn("Pool LEVEL sensor timeout!")
            if EMAIL:
                send_email(pooldb.alert_email, 'Pool LEVEL sensor timeout.', 'Your Pool Level sensor has timed out.')
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool LEVEL Sensor Timeout!")
    elif pool_level_sensor_time_delta < pooldb.max_pool_level_sensor_time_delta and pool_level_timeout_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_sensor_timeout_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", True)
        if PUSHBULLET:
            send_push_notification("Pool Level Sensor Timeout Has Ended", "Your Pool Level Sensor is Back Online!")
        if LOGGING:
            logger.info("Pool LEVEL sensor timeout has ended! Pool level sensor back online.")
        if EMAIL:
            send_email(pooldb.alert_email, 'Pool LEVEL sensor back Online.', 'Your Pool Level sensor is back Online.')

    elif get_pool_level_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
        if pool_level_lowvoltage_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", False)
            if PUSHBULLET:
                send_push_notification("Pool Level Sensor Low Voltage", "The battery is low in your pool level sensor.")
            if LOGGING:
                logger.warn("Pool LEVEL sensor Low Voltage!")
            if EMAIL:
                send_email(pooldb.alert_email, 'Pool LEVEL sensor LOW VOLTAGE.', 'Please replace the Pool LEVEL sensor batteries.')
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool LEVEL Sensor Battery Voltage LOW!")
    elif get_pool_level_sensor_battery_voltage > pooldb.pool_level_sensor_low_voltage and pool_level_lowvoltage_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_level_low_voltage_alert_sent", False)
        update_pool_sensor_status_values("pool_sensor_status", "sensor_status", "pool_level_sensor_ok", True)
        if LOGGING:
            logger.info("Pool LEVEL Sensor Battery level is Normal")

    elif pool_temp_sensor_time_delta > pooldb.max_pool_temp_sensor_time_delta:
        if pool_temp_timeout_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent", True)
            if PUSHBULLET:
                send_push_notification("Pool Temp Sensor Timeout", "Your Pool Temp Sensor has Timed Out!")
            if LOGGING:
                logger.warn("Pool TEMP sensor timeout!")
            if EMAIL:
                send_email(pooldb.alert_email, 'Pool Temp sensor TIME OUT.', 'Your Pool temperature sensor has timed out.')
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool TEMP Sensor Timeout!")
    elif pool_temp_sensor_time_delta < pooldb.max_pool_temp_sensor_time_delta and pool_temp_timeout_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_sensor_timeout_alert_sent", False)
        if PUSHBULLET:
            send_push_notification("Pool Temp Sensor Timeout Has Ended", "Your Pool Temp Sensor is Back Online!")
        if LOGGING:
            logger.info("Pool TEMP Sensor is back online")
        if EMAIL:
            send_email(pooldb.alert_email, 'Pool TEMP sensor back Online.', 'Your Pool Temperature sensor is back Online.')

    elif get_pool_temp_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
        if pool_temp_lowvoltage_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_low_voltage_alert_sent", True)
            if PUSHBULLET:
                send_push_notification("Pool Temp Sensor Low Voltage", "The battery is low in your pool temp sensor.")
            if LOGGING:
                logger.warn("Pool TEMP sensor Low Voltage!")
            if EMAIL:
                send_email(pooldb.alert_email, 'Pool TEMP sensor LOW VOLTAGE.', 'Please replace the Pool floating TEMP sensor batteries.')
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool TEMP Sensor Battery Voltage LOW!")
    elif get_pool_temp_sensor_battery_voltage > pooldb.pool_level_sensor_low_voltage and pool_temp_lowvoltage_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_temp_low_voltage_alert_sent", False)
        if LOGGING:
            logger.info("Pool TEMP Sensor Battery level is Normal")

    elif get_pool_filter_psi > pooldb.pool_filter_max_psi:
        if pool_filter_high_psi_alert_sent == "True":
            pass
        else:
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_filter_psi_alert_sent", True)
            if PUSHBULLET:
                send_push_notification("Pool Filter HIGH PSI", "It is time to BACK FLUSH your pool filter")
            if EMAIL:
                send_email(pooldb.alert_email, 'Pool Filter HIGH PSI', 'Your Pool Filter needs to be backflushed or checked!')
            if LOGGING:
                logger.warn("Pool filter PSI is HIGH!")
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool Filter Pressure HIGH - Backflush your filter!")
    elif get_pool_filter_psi < pooldb.pool_filter_max_psi and pool_filter_high_psi_alert_sent == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_filter_psi_alert_sent", False)
        if LOGGING:
            logger.info("Pool filter PSI is Normal")

    else:
        if DEBUG:
            print ("Everything appears to be OK with the pool sensors!")


def get_pool_level_resistance():
    pool_manual_fill = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill")
    if pool_manual_fill == "True":
        current_timestamp = int(time.time())
        print("Pool is Manually Filling - Automatic Fill disabled!")
        pool_fill_start_time = int(read_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time"))
        pool_fill_total_time = (current_timestamp - pool_fill_start_time) / 60
        update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", pool_fill_total_time)
        print ("Pool has been MANUALLY filling for %s minutes." % pool_fill_total_time)
        if pool_fill_total_time >= pooldb.max_pool_fill_time:
            update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
            if PUSHBULLET:
                send_push_notification("Pool MANUAL Fill Critical Stop", "Your Pool has been MANUALLY filling too long. Critical Stop. Check System!")
            if EMAIL:
               send_email(pooldb.alert_email, 'Pool MANUAL Fill Critical Stop', 'Your Pool has been manually filling too long. Critical Stop. Check System!')
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
            pool_fill_valve("CRITICALCLOSE")
            update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", False)
            if DEBUG:
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
            get_pool_level_percentage(get_pool_level_resistance_value)
            update_pool_sensor_status_values("pool_sensor_status", "pool_level", "pool_level_percentage", pool_level_percentage)
            if DEBUG:
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
                print ("Pool has been filling for %s minutes." % pool_fill_total_time)
                if pool_fill_total_time >= pooldb.max_pool_fill_time:
                    update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
                    if PUSHBULLET:
                        send_push_notification("Pool Fill Critical Stop", "Your Pool has been filling too long. Critical Stop. Check System!")
                    if EMAIL:
                        send_email(pooldb.alert_email, 'Pool Fill Critical Stop', 'Your Pool has been filling too long. Critical Stop. Check System!')
                    update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
                    pool_fill_valve("CRITICALCLOSE")
                    if DEBUG:
                        print("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                pass
            else:
                if critical_stop == "True":
                    if DEBUG:
                        print ("Critical Stop Enabled, pool will not fill! Check System")
                    critical_stop_enabled_warning_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_enabled_warning_sent")
                    if critical_stop_enabled_warning_sent == "False":
                        if PUSHBULLET:
                            send_push_notification("Pool Fill Requested During Critical Stop", "Your Pool Fill is DISABLED due to Critical Stop and is LOW. Please check system!")
                        if EMAIL:
                            send_email(pooldb.alert_email, 'Pool Fill Requested During Critical Stop', 'Your Pool Fill is DISABLED due to Critical Stop and is LOW. Please check system!')
                        update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_enabled_warning_sent", True)
                    pass
                else:
                    if LOGGING:
                        logger.warn("Pool LEVEL is LOW!")
                    pool_fill_valve("OPEN")
                    if DEBUG:
                        print("get_pool_level_resistance() returned pool_level = LOW")


        elif get_pool_level_resistance_value <= pooldb.pool_resistance_ok_level:
            get_pool_level = "OK"
            if pool_is_filling == "True":
                    if LOGGING:
                        logger.info("Pool LEVEL is back to normal!")
                    pool_fill_valve("CLOSE")
            if DEBUG:
                print("get_pool_level_resistance() returned pool_level = OK")
        else:
            if pool_is_filling == "True":
                pool_fill_start_time = int(read_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_start_time"))
                pool_fill_total_time = (current_timestamp - pool_fill_start_time) / 60
                update_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time", pool_fill_total_time)
                print ("Pool has been filling for %s minutes." % pool_fill_total_time)
                if pool_fill_total_time >= pooldb.max_pool_fill_time:
                    update_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop", True)
                    if PUSHBULLET:
                        send_push_notification("Pool Fill Critical Stop", "Your Pool has been filling too long. Critical Stop. Check System!")
                    update_pool_sensor_status_values("pool_sensor_status", "notification_status", "critical_stop_warning_sent", True)
                    pool_fill_valve("CRITICALCLOSE")
                    if DEBUG:
                        print("CRITICAL STOP!! Pool Max Fill Time Exceeded!")
                    if EMAIL:
                        send_email(pooldb.alert_email, 'Pool Fill Critical Stop', 'Your Pool has been filling too long. Critical Stop. Check System!')
                get_pool_level = "MIDWAY"
            else:
                get_pool_level = "MIDWAY"

        if DEBUG:
            print("Our Pool Level is %s." % get_pool_level)


def acid_level():
    acid_level_ok = GPIO.input(acid_level_sensor_pin)
    if acid_level_ok == True:
        acid_level_status = read_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok")
        if acid_level_status == "False":
            update_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok", True)
            if LOGGING:
                logger.info("Pool ACID Level is back to normal.")
        acid_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent")
        if acid_alert_sent == "True":
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent", False)
        if DEBUG:
            print("Acid Level OK")
    else:
        acid_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent")
        if acid_alert_sent == "True":
            acid_alert_sent_time = int(read_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time"))
            acid_alert_sent_delta_time = (current_timestamp - acid_alert_sent_time) / 60
            time_to_next_acid_alert = (pooldb.pool_acid_alert_max_minutes - acid_alert_sent_delta_time)
            if DEBUG:
                print("Acid LOW Alert sent %s minutes ago. " % acid_alert_sent_delta_time)
                print("Next Acid LOW Level Alert will be sent in %s minutes. " % time_to_next_acid_alert)
            if acid_alert_sent_delta_time >= pooldb.pool_acid_alert_max_minutes:
                if PUSHBULLET:
                    send_push_notification("Pool Acid Level is LOW", "Your Acid Level is LOW. Please refill!")
                if EMAIL:
                    send_email(pooldb.alert_email, 'Pool Acid Level is LOW', 'Your Acid Level is LOW. Please refill!')
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time", current_timestamp)
                if LOGGING:
                    logger.warn("Pool ACID Level STILL low. Alert sent again!")
            if DEBUG:
                print("Acid Level LOW")
        else:    
            if DEBUG:
                print("Acid Level LOW")
            if PUSHBULLET:
                send_push_notification("Pool Acid Level is LOW", "Your Acid Level is LOW. Please refill!")
            if EMAIL:
                send_email(pooldb.alert_email, 'Pool Acid Level is LOW', 'Your Acid Level is LOW. Please refill!')
            update_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok", False)
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent", True)
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "acid_level_low_alert_sent_time", current_timestamp)
            if LOGGING:
                logger.warn("Pool ACID Level is LOW!")



def get_pool_temp():
    if DEBUG:
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
        logger.info('get_pool_temp returned %.2fF', get_pool_temp)
        if DEBUG:
            print("get_pool_temp returned %.2fF" % get_pool_temp)

        cnx.close()
        pool_temp = float((get_pool_temp - 32) / 1.8)
        if DEBUG:
             print("pool_temp in C is %.2f" % pool_temp)
        update_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_current_temp", get_pool_temp)

    return pool_temp

    if DEBUG:
        print("Completed get_pool_temp()")



def check_system_status():
    current_military_time = datetime.datetime.now().strftime('%A %b %m, %Y  %H:%M:%S')
    update_pool_sensor_status_values("pool_sensor_status", "system_status", "current_military_time", current_military_time)
    system_reset_required = read_pool_sensor_status_values("pool_sensor_status", "system_status", "system_reset_required")
    critical_stop = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "fill_critical_stop")
    
    if system_reset_required == "True":
        if LOGGING:
            logger.info("System Reset Requested.")
        if DEBUG:
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
        if PUSHBULLET:
            send_push_notification("Pool Fill Control RESET Complete", "Your Pool Fill Control has been reset to normal conditions.")
        if EMAIL:
            send_email(pooldb.alert_email, 'Pool Fill Control RESET Complete', 'Your Pool Fill Control has been reset to normal conditions.')
    else:
        if LOGGING:
            logger.info("System Reset Status = No Reset Requested")
        if DEBUG:
            print("System Reset Status = No Reset Requested")
        led_control(system_run_led, "True")
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "system_run_led", True)


    if critical_stop == "True":
        if LOGGING:
            logger.warn("CRITICAL STOP DETECTED")
            logger.warn("Please check all systems and set [system_reset_required = True] in config file and restart program.")
            logger.warn("This will reset all systems and restart the program.")
        if DEBUG:
            print("")
            print("CRITICAL STOP DETECTED")
            print("Please check all systems and set [system_reset_required = True] in config file and restart program.")
            print("This will reset all systems and restart the program.")


def is_pool_pump_running():
    """ Function to determine if our pool pump is running. """
    if DEBUG:
        print("Started is_pool_pump_running()")
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
        if DEBUG:
            print(
                "pool_pump_running_watts returned %s watts in use by "
                "pump." %
                pool_pump_running_watts)
            update_pool_sensor_status_values("pool_sensor_status", "system_status", "pump_current_watts", pool_pump_running_watts)

    if pool_pump_running_watts > pooldb.max_wattage:
        led_control(pump_run_led, "True")
        pool_pump_running = "Yes"
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", True)
        if DEBUG:
            print("PUMP_RUN_LED should be ON. This is the YELLOW LED")
    else:
        led_control(pump_run_led, "False")
        pool_pump_running = "No"
        update_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led", False)
        if DEBUG:
            print("PUMP_RUN_LED should be OFF. This is the YELLOW LED")

    return pool_pump_running

# This is where we check to see if we can talk to our database. If not, stop and send notification.
def is_database_online():
    pool_database_error_alert_sent = read_pool_sensor_status_values("pool_sensor_status", "notification_status","pool_database_error_alert_sent")
    if DEBUG:
        print("Started is_database_online()")
    try:
        cnx = mysql.connector.connect(user=pooldb.username,
                                      password=pooldb.password,
                                      host=pooldb.servername,
                                      database=pooldb.emoncms_db,
                                      raise_on_warnings=True)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            if LOGGING:
                logger.warn("Database Error: Access Error - Check username or password.")
            if pool_database_error_alert_sent == "False":
                send_push_notification("Pool DB ACCESS DENIED Failure!", "Pool DB ACCESS DENIED Failure. Check your username/password and other access settings and reenable the system!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            if DEBUG:
                print(
                    "Database connection failure: Check your username and "
                    "password")
            exit()    
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            if LOGGING:
                logger.warn("Database Error: Database does not exist.")
            if pool_database_error_alert_sent == "False":
                send_push_notification("Pool DB Connection Failure!", "Pool DB does not exist. Check your settings and reenable the system!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            if DEBUG:
                print("Database does not exist. Please check your settings.")
            exit()    
        elif err.errno == errorcode.CR_CONN_HOST_ERROR:
            if LOGGING:
                logger.warn("Database Error: Cannot connect to MySQL database.")
            if pool_database_error_alert_sent == "False":
                send_push_notification("Pool DB Connection Failure!", "Cannot Connect to MySQL Server. Check your settings and reenable the system!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            if DEBUG:
                print("MySQL Server Error: Cannot connect to MySQL Server. Check connection and reset system.")
            exit()    
        else:
            if LOGGING:
                logger.warn("Database Error: Unknown Error.")
            if pool_database_error_alert_sent == "False":
                send_push_notification("Pool DB Connection Failure!", "Pool DB error. Check your settings and reenable the system!")
                update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", True)
            if DEBUG:
                print(
                    "Unknown database error, please check all of your "
                    "settings.")
            exit()    
    else:
        if pool_database_error_alert_sent == "True":
            update_pool_sensor_status_values("pool_sensor_status", "notification_status", "pool_database_error_alert_sent", False)
            send_push_notification("Pool DB Back Online!", "Your Pool Database is back online. System is Normal!")
            cnx.close()
            pass
        else:
            cnx.close()
            pass

# Here we go.......
def main():
    if LOGGING:
        logger.info("pool_control_master started")
    is_database_online()
    mightyhat_serial_setup()
    check_system_status()
    get_pool_temp()
    is_pool_pump_running()
    check_pool_sensors()
    get_pool_level_resistance()
    acid_level()

if __name__ == '__main__':
    main()


