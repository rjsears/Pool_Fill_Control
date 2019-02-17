#!/usr/bin/python

## Setup our pool_control Database Connection. This database is where we store all of our system settings. Do
## not confuse it with our environmental data dabatabse information located below:

__author__ = 'Richard J. Sears'
VERSION = "V3.5.0 (2019-02-16)"
# richard@sears.net

servername = "mysql"
username = "pool_master"  # Your main MySQL admin username or username that is the exact same for both databases
password = "your_password_here"  # Your main MySQL admin password or password that is exact same for both databases
database = "pool_control"  # The name of your pool_control (or other) database.
alert_email = 'your_email@domain.net'

## Here is the EmonCMS database where all of our environment data is stored (temps, humidity, pool level, etc).
## Setup our EmonCMS Database Connection
emoncms_servername = "phx-emoncms"
emoncms_username = "emoncms"
emoncms_password = "put_your_password_here"
emoncms_db = "emoncms"
