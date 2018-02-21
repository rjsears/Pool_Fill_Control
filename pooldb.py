#!/usr/bin/python

""" Config file for Pool_Fill_Control"""

## Set Notification Types
DEBUG = True
LOGGING = True
EMAIL = True
PUSHBULLET = True
alert_email = 'your_email@addresshere.com'

## Setup our Database Connection
servername = "localhost"
username = "pool_control"  # Your main MySQL admin username or username that is the exact same for both databases
password = "your_password_here"  # Your main MySQL admin password or password that is exact same for both databases
emoncms_db = "emoncms"  # The name of your emoncms (or other) database.

# Set up some alerting so we know when the pool is getting filled up and when it is done.
pushbilletAPI = "o.xxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # pushbullet API token (http://www.pushbullet.com)

## Pool temperature Sensor Settings
pool_temp_table = "feed_274"
pool_temp_sensor_battery_table = "feed_151"
pool_temp_sensor_low_voltage = 2.9
max_pool_temp_sensor_time_delta = 3000

## What is the table name for our pool_level feed and other settings for our pool_level_sensor?
pool_level_table = "feed_222"
pool_level_sensor_battery_table = "feed_220"

# At what voltage do we consider the pool_level_sensor to have low batteries?
pool_level_sensor_low_voltage = 2.9

# After how many seconds of no database activity from our pool_level_sensor do we consider it offline?
max_pool_level_sensor_time_delta = 2000

# How many Pool Level Sensor Timeouts before we do something?
max_pool_level_sensor_timeouts = 10

## The HIGHER  the Resistance, the LOWER the pool!!!
# What is the Pool Level Max Resistance before we need to refill the pool?
pool_resistance_critical_level = 740  # set back to 740 when done testing)

# What is the pool level low resistance when we decide the pool is full enout?
pool_resistance_ok_level = 710

# How long to allow the pool to fill before sending an error? (in minutes)
max_pool_fill_time = 120 

# What is the table name for our pool resistance?
pool_resistance_table = "feed_221"

## What is the table name for our pool_running_watts feed?
pump_running_watts_table = "feed_153"

## What is the table name for our pool_filter_psi?
pool_filter_psi_table = "feed_273"
pool_filter_max_psi = 40


#pool acid realert time: How many minutes between low acid alerts do we want?
pool_acid_alert_max_minutes = 2880


## Do we have a pool water sensor and are we tracking the pool water temp? (Generally user for accurate pH readings).
temp_probe = "Yes"
temp_probe_table = "feed_274"

## This is for our pH and ORP probes. This is the information needed to store our pH and ORP reading to our
## two emoncms servers
##
## Do we want to use or do we have the pH and ORP probes installed?
ph_probe = "Yes"  # Yes or No
ph_node = "pool_ph"  # This will be the Node_ID that shows up in your inputs if logging to emoncms
ph_probe_baud = 38400

orp_probe = "Yes"  # Yes or No
orp_node = "pool_orp"  # This will be the Node_ID that shows up in your inputs if logging to emoncms
orp_probe_baud = 38400

## Do we have multiple emoncms servers and do we want them turned on...?
# Server 1 Information
emoncms_server1 = "Yes"
server1 = "emonpi"  # This could be an IP address, localhost, or an FQDN
emoncmspath1 = "emoncms"  # This is the path, for example if you want http://www.yourdomain.com/emoncms/
# you would put "emoncms" here.
apikey1 = "Your emoncms API key here"

# Server 2 Information
emoncms_server2 = "Yes"
server2 = "emoncms2"
emoncmspath2 = ""
apikey2 = "Your emoncms API key here"

# Used for Sprinkler Bypass
sprinkler_bypass = "Yes"  # Set this to "No" to disable all sprinkler checks
sprinkler_type = "Rachio"  # Timer or Rachio - sprinkler_bypass must be set to "Yes" for this to make any difference

# If you have a Rachio Sprinkler System, this is the curl request to get the sprinkler status.
# You must have your own system, you must get your Auth:Bearer ID as well as you device ID
# from Rachio in order to use this subprocess.
rachio_url = 'curl -s -X  GET -H "Content-Type: application/json" -H "Authorization: Bearer xxxxxxxxxxxxxxxxxxxxxxxxxx" https://api.rach.io/1/public/device/xxxxxxxxxxxxxxxxxxxxxxxxxx/current_schedule'

############################################################################################################################
########## Runtime checking and maximum fill times - This is for the automatic system, not the manual python check...
############################################################################################################################
checktime = 60  # How often (in seconds) do we want to check the pool level? This is how often the pool_level()
# subroutine will be run which checks the database for the pool level. We will not change the
# state of the pool fill valve outside of this subroutine, so don't set it to something
# like 5 hours unless you want a flooded yard!

# Each "checktime cycle" will occur at the interval you specify here.

#######  VERY VERY VERY IMPORTANT ####
# We now support a watchdog timer. I have set the timer for 90 seconds based on this 60 second checktime. If you change this checktime
# you MUST MUST MUST change the timer in /etc/systemd/system/pool_control.service otherwise your script will restart every
# 90 seconds!!!


##########################################################################################################################
maxruntime = 100  # What is the maximum number of checktime cycles you want to let your pool fill? For example
# if you put 60 seconds above for checktime, and 180 here, it will be 60 seconds * 180 readings
# which will be a total of three hours. Once this number is hit, if the pool still is not full,
# we force the pool fill valve closed and notify you (if notification is set on) that there is
# a problem.

# WARNING * WARNING * WARNING => There is NO time check when running a manual fill. If you fail to shut off your manual
# fill, your pool will overflow!
############################################################################################################################


## Set the MAXIMUM idle wattage of your pool pump/equipment. If the reading is over this wattage, the pool will not fill since the
## pump would be running. If you do not care if your pump is running while you are filling your pool, set this super high, like 5000.
max_wattage = 200

## Do we have a MightyHat installed with an LCD screen and if so, do we want to output mesages to the LCD screen?
MightyHat = "True"
