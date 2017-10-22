#!/usr/bin/python
""" Python script to manually check pool temp,level and PSI sensors """

# Can be run manually or via cron
__author__ = 'Richard J. Sears'
VERSION = "V1.00 (2017-10-21)"
# richard@sears.net

import pooldb  # Database information
import mysql.connector
from mysql.connector import errorcode
import time
import os
import RPi.GPIO as GPIO  # Import GPIO Library
from pushbullet import Pushbullet

# Do not use pooldb.DEBUG here as pooldb.DEBUG normally will be FALSE and
# if you are manually running the sensor check we assume that you will
# want to see the results on STDOUT.
DEBUG = True

# Our relay for the sprinkler valve is on GPIO 17 (Physical Pin 11)
POOL_FILL_RELAY = 17

# Relay that controls power to the transformer that operates
# the sprinkler valve (Physical Pin 19)
POOL_FILL_TRANSFORMER_RELAY = 26

# Setup our GPIO Pins
GPIO.setwarnings(False)  # Don't tell me about GPIO warnings.
GPIO.setmode(GPIO.BCM)  # Use BCM Pin Numbering Scheme
GPIO.setup(POOL_FILL_RELAY, GPIO.OUT)
GPIO.setup(POOL_FILL_TRANSFORMER_RELAY, GPIO.OUT)

# Pool_Fill_Valve controls pool sprinkler relay as well as pool sprinkler
# transformer relay.
def pool_fill_valve(openclose):
    if openclose == "OPEN":
       os.mknod("/root/pool_control/check_pool_sensors/pool_is_filling")
       GPIO.output(POOL_FILL_TRANSFORMER_RELAY, True)  # Turns on the Sprinkler Transformer
       if DEBUG:
            print("pool_fill_valve called with OPEN command")
            print("POOL_FILL_TRANSFORMER_RELAY is now powered and pool "
                "transformer is now ACTIVE")
       GPIO.output(POOL_FILL_RELAY, True)  # Turns on the sprinkler valve
       os.system('echo "POOL IS FILLING" > /root/pool_control/check_pool_sensors/FILLING_STATUS.txt')
       send_push_notification("Your Pool Is Filling", "Your swimming pool is refilling.")
       if DEBUG:
           print("POOL_FILL_RELAY is now powered and sprinkler valve solenoid is now powered.")
           print("Both relays should now be active and Sprinkler valve should be open and water should be running.")
    elif openclose == "CLOSE":
        GPIO.output(POOL_FILL_RELAY, False)  # Turns off the sprinkler valve
        if DEBUG:
            print("pool_fill_valve called with CLOSE command")
            print("POOL_FILL_RELAY is now powered OFF and sprinkler valve "
                "solenoid is no longer powered.")
        GPIO.output(POOL_FILL_TRANSFORMER_RELAY, False)  # Turns off the Sprinkler Transformer
        os.system('echo "POOL IS ** NOT ** FILLING" > /root/pool_control/check_pool_sensors/FILLING_STATUS.txt')
        send_push_notification("Your Pool Is Done Filling", "Your swimming pool is done refilling.")
        os.remove("/root/pool_control/check_pool_sensors/pool_is_filling")
        if DEBUG:
            print("POOL_FILL_TRANSFORMER_RELAY is now powered off and pool transformer is now OFF.")
            print("Both relays should no longer be active. Sprinkler valve and transformer are now off.")

def check_pool_sensors():
    get_pool_level_sensor_time = 0
    get_pool_temp_sensor_time = 0
    get_pool_level_sensor_battery_voltage = 0
    get_pool_temp_sensor_battery_voltage = 0
    get_pool_filter_psi = 0
    current_timestamp = int(time.time())
    if DEBUG:
        print ("Current unix datetime stamp is: %s" % current_timestamp)

    try:
        cnx = mysql.connector.connect(user=pooldb.username,
                                      password=pooldb.password,
                                      host=pooldb.servername,
                                      database=pooldb.emoncms_db)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            if DEBUG:
                print(
                    "Database connection failure: Check your username and "
                    "password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            if DEBUG:
                print("Database does not exist. Please check your settings.")
        else:
            if DEBUG:
                print(
                    "Unknown database error, please check all of your "
                    "settings.")
    else:
        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT time FROM `%s` ORDER by time DESC LIMIT 1") % (
            pooldb.pool_level_table))

        for data in cursor:
            get_pool_level_sensor_time = int("%1.0f" % data)
            cursor.close()
            if DEBUG:
                print(
                    "Pool LEVEL sensor last updated at: %s" %
                    get_pool_level_sensor_time)

        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
            pooldb.pool_level_sensor_battery_table))

        for data in cursor:
            get_pool_level_sensor_battery_voltage = float("%1.2f" % data)
            cursor.close()
            if DEBUG:
                print(
                    "Pool LEVEL sensor battery voltage is: %s" %
                    get_pool_level_sensor_battery_voltage)

        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT time FROM `%s` ORDER by time DESC LIMIT 1") % (
            pooldb.pool_temp_table))

        for data in cursor:
            get_pool_temp_sensor_time = int("%1.0f" % data)
            cursor.close()
            if DEBUG:
                print(
                    "Pool TEMP sensor last updated at: %s" %
                    get_pool_temp_sensor_time)

        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
            pooldb.pool_temp_sensor_battery_table))
            for data in cursor:
            get_pool_temp_sensor_battery_voltage = float("%1.2f" % data)
            cursor.close()
            if DEBUG:
                print(
                    "Pool TEMP sensor battery voltage is: %s" %
                    get_pool_temp_sensor_battery_voltage)

        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
            pooldb.pool_filter_psi_table))
        for data in cursor:
            get_pool_filter_psi = int("%1.0f" % data)
            cursor.close()
            if DEBUG:
                print(
                    "Pool FILTER PSI is: %s" %
                    get_pool_filter_psi)

    cnx.close()
pool_level_sensor_time_delta = current_timestamp - get_pool_level_sensor_time
    pool_temp_sensor_time_delta = current_timestamp - get_pool_temp_sensor_time

    if DEBUG:
        print ("Time dfference between last pool LEVEL sensor reading is: %s "
            "seconds." % pool_level_sensor_time_delta)
        print ("Time dfference between last pool TEMP sensor reading is: %s "
            "seconds." % pool_temp_sensor_time_delta)
        print ("Current Filter Pressure is: %s PSI." % get_pool_filter_psi)
    if pool_level_sensor_time_delta > pooldb.max_pool_level_sensor_time_delta:
        if os.path.isfile('/root/pool_control/check_pool_sensors/pool_level_sensor_alert_sent'):
            pass
        else:
            send_push_notification("Pool Level Sensor Timeout", "Your Pool Level Sensor has Timed Out!")
            os.mknod("/root/pool_control/check_pool_sensors/pool_level_sensor_alert_sent")
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool LEVEL Sensor Timeout!")
    elif get_pool_level_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
        if os.path.isfile('/root/pool_control/check_pool_sensors/pool_level_low_voltage_alert_sent'):
            pass
        else:
            send_push_notification("Pool Level Sensor Low Voltage", "The battery is low in your pool level sensor.")
            os.mknod("/root/pool_control/check_pool_sensors/pool_level_low_voltage_alert_sent")
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool LEVEL Sensor Battery Voltage LOW!")
    elif pool_temp_sensor_time_delta > pooldb.max_pool_temp_sensor_time_delta:
        if os.path.isfile('/root/pool_control/check_pool_sensors/pool_temp_sensor_alert_sent'):
            pass
        else:
            send_push_notification("Pool Temp Sensor Timeout", "Your Pool Temp Sensor has Timed Out!")
            os.mknod("/root/pool_control/check_pool_sensors/pool_temp_sensor_alert_sent")
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool TEMP Sensor Timeout!")
    elif get_pool_temp_sensor_battery_voltage < pooldb.pool_level_sensor_low_voltage:
        if os.path.isfile('/root/pool_control/check_pool_sensors/pool_temp_sensor_low_voltage_alert_sent'):
            pass
        else:
            send_push_notification("Pool Temp Sensor Low Voltage", "The battery is low in your pool temp sensor.")
            os.mknod("/root/pool_control/check_pool_sensor/pool_temp_sensor_low_voltage_alert_sent")
        if DEBUG:
            print ("* * * * WARNING * * * *")
            print ("Pool TEMP Sensor Battery Voltage LOW!")
    elif get_pool_filter_psi > pooldb.pool_filter_max_psi:
        if os.path.isfile('/root/pool_control/check_pool_sensors/pool_filter_psi_alert_sent'):
            pass
        else:
            notifications.send_notification('FILTER_HIGH_PSI')
            send_push_notification("Pool Filter HIGH PSI", "It is time to BACK FLUSH your pool filter")
            os.mknod('/root/pool_control/check_pool_sensors/pool_filter_psi_alert_sent')
    else:
        if DEBUG:
            print ("Everything appears to be OK with the pool sensors!")

def get_pool_level_resistance():
    """ Function to get the current level of our pool from our MySQL DB. """
    global get_pool_level
    global get_pool_level_resistance_value
    try:
        cnx = mysql.connector.connect(user=pooldb.username,
                                      password=pooldb.password,
                                      host=pooldb.servername,
                                      database=pooldb.emoncms_db)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            if DEBUG:
                print("Database connection failure: Check your username and password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            if DEBUG:
                print("Database does not exist. Please check your settings.")
        else:
            if DEBUG:
                print("Unknown database error. Please check all of your settings.")
    else:
        cursor = cnx.cursor(buffered=True)
        cursor.execute(("SELECT data FROM `%s` ORDER by time DESC LIMIT 1") % (
            pooldb.pool_resistance_table))

        for data in cursor:
            get_pool_level_resistance_value = int("%1.0f" % data)
            cursor.close()
            if DEBUG:
                print("pool_sensors: Pool Resistance is: %s " % get_pool_level_resistance_value)
                print("pooldb: Static critical pool level resistance set at ("
                    "%s)." % pooldb.pool_resistance_critical_level)
                print("pooldb: Static normal pool level resistance set at (%s)." %
                    pooldb.pool_resistance_ok_level)
        cnx.close()

    if get_pool_level_resistance_value >= pooldb.pool_resistance_critical_level:
        get_pool_level = "LOW"
        if os.path.isfile('/root/pool_control/check_pool_sensors/pool_is_filling'):
            if DEBUG:
                print("Pool is currently filling - pool_is_filling is present")
            pass
        else:
            pool_fill_valve("OPEN")
            if DEBUG:
                print("get_pool_level_resistance() returned pool_level = LOW")
    elif get_pool_level_resistance_value <= pooldb.pool_resistance_ok_level:
        get_pool_level = "OK"
        if os.path.isfile('/root/pool_control/check_pool_sensors/pool_is_filling'):
                pool_fill_valve("CLOSE")
        if DEBUG:
            print("get_pool_level_resistance() returned pool_level = OK")
    else:
        get_pool_level = "MIDWAY"

    if DEBUG:
        print("Our Pool Level is %s." % get_pool_level)



# We use Push Bullet to send out all of our alerts
def send_push_notification(title, message):
        pb = Pushbullet(pooldb.pushbilletAPI)
        push = pb.push_note(title, message)

# Here we go.......
def main():
    check_pool_sensors()
    get_pool_level_resistance()


if __name__ == '__main__':
    main()
