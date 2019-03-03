#!/usr/bin/python
# Main Notifications module that handles all logging and notifications system
# wide. This resides in the Utilities directory.
#
# Current Notification Methods include:

# DEBUG
# This is CONSOLE debugging and toggled via the "Console Debugging" switch on the main web interface

# Logging
# This provides system logging of INFO, WARN and DEBUG messages. Logging  level is set in pooldb.py

# Notify
# This function reads notification configurations and provides notification for the following:
# E-Mail (alert email set in pooldb.py)
# Pushbullet
# Twilio (SMS)

# This script is not intended to be run manually, rather it is called by other modules.
# For use with pool_control_master_db.py V3.5.0

# Last updated 2019-02-16 - Switch to MySQL DB from flat file.


__author__ = 'Richard J. Sears'
VERSION = "V3.5.1 (2019-03-03)"
# richard@sears.net

import time
import logging.handlers
import subprocess
from pushbullet import Pushbullet
from twilio.rest import Client
import db_info
import mysql.connector
from mysql.connector import Error
import ConfigParser

config = ConfigParser.ConfigParser()

# Setup Logging Here
def read_logging_config(file, section, status):
    pathname = '/var/www/' + file
    config.read(pathname)
    if status == "LOGGING":
        current_status = config.getboolean(section, status)
    else:
        current_status = config.get(section, status)
    return current_status

LOG_LEVEL = read_logging_config("logging_config", "logging", "LEVEL")
LOGGING = read_logging_config("logging_config", "logging", "LOGGING")
log = logging.getLogger(__name__)
if LOGGING:
    log.disabled = False
    level = logging._checkLevel(LOG_LEVEL)
    log.setLevel(level)
else:
    log.disabled = True

## We need to have our database functions here instead of calling use_database.py
## This resolves an circular import issue.


def notifications_read_database(table, column):
    try:
        connection = mysql.connector.connect(user=db_info.username,
                                      password=db_info.password,
                                      host=db_info.servername,
                                      database=db_info.database)
        cursor = connection.cursor(buffered=True)
        cursor.execute(("SELECT %s FROM %s") % (column, table))
        for data in cursor:
            database_value = (data[0])
            return database_value
        cursor.close()
        connection.close()
    except Error as error :
        print("Failed to read record from database: {}".format(error))
        log.warning( "Failed to read record from database: {}".format(error))
        exit()
    finally:
        if(connection.is_connected()):
            connection.close
            #log.info( "use_database.py:read_database() Database connection closed.")

def notifications_update_database(table,column,value):
    try:
        connection = mysql.connector.connect(user=db_info.username,
                                      password=db_info.password,
                                      host=db_info.servername,
                                      database=db_info.database)
        cursor = connection.cursor(buffered=True)
        sql_update = "UPDATE " + table + " SET " + column + " = %s"
        cursor.execute(sql_update, (value,))
        connection.commit()
        cursor.close()
        connection.close()
    except Error as error :
        print("Failed to Update record in database: {}".format(error))
        log.warning( "Failed to UPDATE database: {}".format(error))
        exit()
    finally:
        if(connection.is_connected()):
            connection.close


current_timestamp = int(time.time())


# Setup to send email via the builtin linux mail command.
# Your local system must be configured already to send mail or this will fail.
def send_email(recipient, subject, body):
    process = subprocess.Popen(['mail', '-s', subject, recipient],stdin=subprocess.PIPE)
    process.communicate(body)

# Setup to send out Pushbillet alerts. Pushbullet config is in pooldb.py
def send_push_notification(title, message):
    pb = Pushbullet(db_info.pushbilletAPI)
    push = pb.push_note(title, message)

# Setup to send SMS Text messages via Twilio. Configured in pooldb.py
def send_sms_notification(body):
    client = Client(db_info.twilio_account, db_info.twilio_token)
    message = client.messages.create(to=db_info.twilio_to, from_=db_info.twilio_from, body=body)

# Notify system for email, pushbullet and sms (via Twilio)
def notify(sub_system_notifications, title, message):
    log.debug("notify() called with {}, {} and {}.".format(sub_system_notifications, title, message))
    sub_system_notifications = notifications_read_database("notification_settings", sub_system_notifications)
    EMAIL = notifications_read_database("notification_methods", "email")
    PUSHBULLET = notifications_read_database("notification_methods", "pushbullet")
    SMS = notifications_read_database("notification_methods", "sms")

    if PUSHBULLET and sub_system_notifications:
        send_push_notification(title,message)
        log.info( "PB Notification Sent with: {}".format(message))
    else:
        pass
    if EMAIL and sub_system_notifications:
        send_email(db_info.alert_email, title, message)
        log.info( "Email sent with: {}".format(message))
    else:
        pass
    if SMS and sub_system_notifications:
        send_sms_notification(message)
        log.info( "SMS sent with: {}".format(message))
    else:
        pass
    log.debug( "notify() completed.")

def main():
    print("Not intended to be run directly.")
    print("This is the systemwide Notification module.")
    print("It is called by other modules.")
    exit()


if __name__ == '__main__':
    main()
