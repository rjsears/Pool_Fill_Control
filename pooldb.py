#!/usr/bin/python

# Set systemwide loglevel here:
# INFO
# WARN
# DEBUG
loglevel = "INFO"

__author__ = 'Richard J. Sears'
VERSION = "V3.5.0 (2019-02-16)"
# richard@sears.net


""" Config file for Pool_Fill_Control"""
check_url = 'www.google.com'

# Set DB here to read pump watts (only) from DB via emoncms or
# set NODEJS to use Russ Goldin's nodeJS Pump control software
# https://github.com/tagyoureit/nodejs-poolController
PUMP_DATA = "NODEJS"
PUMP_DATA_URL = "http://localhost:3000/pump"
PUMP_DATA_TEST_URL = "localhost:3000"
PUMP_START_URL = "http://localhost:3000/pumpCommand/run/pump/1"
PUMP_STOP_URL = "http://localhost:3000/pumpCommand/off/pump/1"
PUMP_PROGRAM1_URL = "http://localhost:3000/pumpCommand/run/pump/1/program/1"
PUMP_PROGRAM2_URL = "http://localhost:3000/pumpCommand/run/pump/1/program/2"
PUMP_PROGRAM3_URL = "http://localhost:3000/pumpCommand/run/pump/1/program/3"
PUMP_PROGRAM4_URL = "http://localhost:3000/pumpCommand/run/pump/1/program/4"


## Pool temperature Sensor Settings
pool_temp_table = "feed_53"
pool_temp_sensor_temp_table = "feed_54"
pool_temp_sensor_battery_table = "feed_52"
pool_temp_sensor_humidity_table = "feed_55"
pool_temp_sensor_low_voltage = 2.9
max_pool_temp_sensor_time_delta = 3000

## What is the table name for our pool_level feed and other settings for our pool_level_sensor?
pool_level_table = "feed_81"
pool_level_sensor_battery_table = "feed_80"
pool_level_sensor_humidity_table = "feed_83"
pool_level_sensor_temp_table = "feed_82"

# Settings for Power & Solar if using Solar Module to manage pump
power_total_use = "feed_49"
power_importing = "feed_42"
power_solar = "feed_46"

# Other temp sensors if you are using them....
garage_temp_sensor_humidity_table = "feed_69"
garage_temp_sensor_battery_table = "feed_70"
garage_temperature_table = "feed_68"
attic_temp_sensor_battery_table = "feed_74"
attic_temperature_table = "feed_75"


# At what voltage do we consider the pool_level_sensor to have low batteries?
pool_level_sensor_low_voltage = 2.9

# After how many seconds of no database activity from our pool_level_sensor do we consider it offline?
max_pool_level_sensor_time_delta = 2000

# How many Pool Level Sensor Timeouts before we do something?
max_pool_level_sensor_timeouts = 10

# How long to allow the pool to fill before sending an error? (in minutes)
max_pool_fill_time = 130

# How long to fill the pool each time we ask Alexa to fill it...
alexa_max_pool_fill_time = 60

# What is the table name for our pool resistance?
pool_resistance_table = "feed_56"

## What is the table name for our pool_running_watts feed?
pump_running_watts_table = "feed_24"

## What is the table name for our pool_filter_psi?
pool_filter_psi_table = "feed_67"
pool_filter_max_psi = 20
pool_filter_max_psi_reset = 15 

#pool acid realert time: How many minutes between low acid alerts do we want?
pool_acid_alert_max_minutes = 2880

# How many gallons have we used to fill the pool?
pool_gallons_total = "feed_65"

## Do we have a pool water sensor and are we tracking the pool water temp? (Generally user for accurate pH readings).
temp_probe = "Yes"
temp_probe_table = "feed_53"

## This is for our pH and ORP probes. This is the information needed to store our pH and ORP reading to our
## two emoncms servers
##
## Do we want to use or do we have the pH and ORP probes installed?
ph_probe = "Yes"  # Yes or No
ph_node = int(40)
#ph_node = "pool_ph"  # This will be the Node_ID that shows up in your inputs if logging to emoncms
ph_probe_baud = 38400

orp_probe = "Yes"  # Yes or No
orp_node = int(41)
#orp_node = "pool_orp"  # This will be the Node_ID that shows up in your inputs if logging to emoncms
orp_probe_baud = 9600

## Do we have multiple emoncms servers and do we want them turned on...?
# Server 1 Information
emoncms_server1 = "No"
server1 = "emonpi"  # This could be an IP address, localhost, or an FQDN
emoncmspath1 = "emoncms"  # This is the path, for example if you want http://www.yourdomain.com/emoncms/
# you would put "emoncms" here.
apikey1 = "api_key_here"

# Server 2 Information
emoncms_server2 = "No"
server2 = "phx-emoncms"
emoncmspath2 = ""
apikey2 = "api_key_here"

# Used for Sprinkler Bypass
sprinkler_bypass = "Yes"  # Set this to "No" to disable all sprinkler checks
sprinkler_type = "Rachio"  # Timer or Rachio - sprinkler_bypass must be set to "Yes" for this to make any difference

# If you have a Rachio Sprinkler System, this is the curl request to get the sprinkler status.
# You must have your own system, you must get your Auth:Bearer ID as well as you device ID
# from Rachio in order to use this subprocess.
rachio_url = 'curl -s -X  GET -H "Content-Type: application/json" -H "Authorization: Bearer jjsjdjjds-skksdkkdk-yyey" https://api.rach.io/1/public/device/device_id/current_schedule'


## Set the MAXIMUM idle wattage of your pool pump/equipment. If the reading is over this wattage, the pool will not fill since the
## pump would be running. If you do not care if your pump is running while you are filling your pool, set this super high, like 5000.
max_wattage = 100

## Do we have a MightyHat installed with an LCD screen and if so, do we want to output mesages to the LCD screen?
MightyHat = "True"
