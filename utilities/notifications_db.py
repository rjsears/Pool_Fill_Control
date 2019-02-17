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
PCM_VERSION = "pool_control_master_db.VERSION"

import pooldb
import time
import logging
import subprocess
from pushbullet import Pushbullet
from twilio.rest import Client
import db_info
import mysql.connector
from mysql.connector import Error


## We need to have our database functions here instead of calling use_database.py
## This resolves an circular import issue.


def read_database(table, column):
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
        log("WARN", "Failed to read record from database: {}".format(error))
        exit()
    finally:
        if(connection.is_connected()):
            connection.close
            #log("INFO", "use_database.py:read_database() Database connection closed.")

def update_database(table,column,value):
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
        log("WARN", "Failed to UPDATE database: {}".format(error))
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
    pb = Pushbullet(pooldb.pushbilletAPI)
    push = pb.push_note(title, message)

# Setup to send SMS Text messages via Twilio. Configured in pooldb.py
def send_sms_notification(body):
    client = Client(pooldb.twilio_account, pooldb.twilio_token)
    message = client.messages.create(to=pooldb.twilio_to, from_=pooldb.twilio_from,
                                         body=body)

# Output debugging messages to the console if set via the web interface
def debug(message):
    DEBUG = read_database("notification_methods", "debug")
    if DEBUG:
        print(message)

def verbose_debug(message):
    VERBOSE_DEBUG = read_database("notification_methods", "verbose_debug")
    if VERBOSE_DEBUG:
        print(message)

# System wide logging configuration
def log(loglevel, message):
    LOGGING = read_database("notification_methods", "logging")
    if LOGGING:
        logger = logging.getLogger(__name__)
        if not len(logger.handlers):
            level = logging._checkLevel(loglevel)
            handler = logging.FileHandler('/var/log/pool_control_master_db.log')
            formatter = logging.Formatter('%(filename)2s:%(lineno)s - %(funcName)3s: %(asctime)s %(levelname)3s %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel("DEBUG")
            logger.filemode = 'a'
            logger.log(level, message)
        else:
            level = logging._checkLevel(loglevel)
            logger.log(level, message)

def log_flask(loglevel, message):
    LOGGING = read_database("notification_methods", "logging")
    if LOGGING:
        logger = logging.getLogger(__name__)
        if not len(logger.handlers):
            level = logging._checkLevel(loglevel)
            handler = logging.FileHandler('/var/log/flask_logging.log')
            formatter = logging.Formatter('%(filename)2s:%(lineno)s - %(funcName)3s: %(asctime)s %(levelname)3s %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel("DEBUG")
            logger.filemode = 'a'
            logger.log(level, message)
        else:
            level = logging._checkLevel(loglevel)
            logger.log(level, message)


# Notify system for email, pushbullet and sms (via Twilio)
def notify(sub_system_notifications, title, message):
    sub_system_notifications = read_database("notification_settings", sub_system_notifications)
    EMAIL = read_database("notification_methods", "email")
    PUSHBULLET = read_database("notification_methods", "pushbullet")
    SMS = read_database("notification_methods", "sms")


    if PUSHBULLET and sub_system_notifications:
        send_push_notification(title,message)
    else:
        pass
    if EMAIL and sub_system_notifications:
        send_email(db_info.alert_email, title, message)
    else:
        pass
    if SMS and sub_system_notifications:
        send_sms_notification(message)
    else:
        pass

def main():
    print("Not intended to be run directly.")
    print("This is the systemwide Notification module.")
    print("It is called by other modules.")
    exit()


if __name__ == '__main__':
    main()
