#!/usr/bin/python

## Setup our pool_control Database Connection. This database is where we store all of our system settings. Do
## not confuse it with our environmental data dabatabse information located below:

__author__ = 'Richard J. Sears'
VERSION = "V3.5.0 (2019-02-16)"
# richard@sears.net

servername = "mysql"
username = "pool_master"  # Your main MySQL admin username or username that is the exact same for both databases
password = "P@ssw)rd"  # Your main MySQL admin password or password that is exact same for both databases
database = "pool_control"  # The name of your pool_control (or other) database.



## Here is the EmonCMS database where all of our environment data is stored (temps, humidity, pool level, etc).

## Setup our EmonCMS Database Connection
emoncms_servername = "phx-emoncms"
emoncms_username = "emoncms"
emoncms_password = "P@ssw)rd"
emoncms_db = "emoncms"


## Information for our Influx Databases:
# InfluxDB connections settings
influx_host = 'scripts'
influx_port = 8086
influx_user = 'pool_control'
influx_password = 'P@ssw)rd'
influx_dbname = 'pool_control'
influx_dbname_energy = 'energy_management'

# Second InfluxDB connections settings (if any)
influx2_host = 'haarp'
influx2_port = 8086
influx2_user = 'pool_control'
influx2_password = 'P@ssw)rd'
influx2_dbname = 'pool_control'
influx2_dbname_energy = 'energy_management'

## Info for our notifications_db.py
## Set Notification Accounts#
alert_email = 'your_email@domain.com'
twilio_from = '+18585551212'
twilio_account = 'your_account_number_here'
twilio_token = 'your_token_here'
twilio_to = '+18585551212'
pushbilletAPI = "your_pushbullet_token_here"  # pushbullet API token (http://www.pushbullet.com)
