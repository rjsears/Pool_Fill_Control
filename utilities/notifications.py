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
# For use with pool_control_master.py V3.4.6

# Last updated 2018-09-23


__author__ = 'Richard J. Sears'
PCM_VERSION = "pool_control_master.VERSION"

import sys
sys.path.append('../')
import time
import ConfigParser
import pooldb
import logging
import subprocess
from pushbullet import Pushbullet
from twilio.rest import Client

config = ConfigParser.ConfigParser()
current_timestamp = int(time.time())

alert_email = pooldb.alert_email


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
    DEBUG = read_pool_sensor_status_values("pool_sensor_status",
                                           "notification_methods", "debug")
    if DEBUG == "True":
        print(message)

def verbose_debug(message):
    VERBOSE_DEBUG = read_pool_sensor_status_values("pool_sensor_status",
                                           "notification_methods", "verbose_debug")
    if VERBOSE_DEBUG == "True":
        print(message)

# System wide logging configuration
def log(loglevel, message):
    LOGGING = read_pool_sensor_status_values("pool_sensor_status",
                                             "notification_methods", "logging")
    if LOGGING == "True":
        logger = logging.getLogger(__name__)
        if not len(logger.handlers):
            level = logging._checkLevel(loglevel)
            handler = logging.FileHandler('/var/log/pool_control_master.log')
           # formatter = logging.Formatter('[%(filename)s:%(lineno)s - %(funcName)5s() ] %(message)s')
            formatter = logging.Formatter('%(filename)2s:%(lineno)s - %(funcName)3s: %(asctime)s %(levelname)3s %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(pooldb.loglevel)
            logger.filemode = 'a'
            logger.log(level, message)
        else:
            level = logging._checkLevel(loglevel)
            logger.log(level, message)

# Notify system for email, pushbullet and sms (via Twilio)
def notify(sub_system_notifications, title, message):
    sub_system_notifications = read_pool_sensor_status_values(
        "pool_sensor_status", "notification_settings",
        sub_system_notifications)
    EMAIL = read_pool_sensor_status_values("pool_sensor_status",
                                           "notification_methods", "email")
    PUSHBULLET = read_pool_sensor_status_values("pool_sensor_status",
                                                "notification_methods",
                                                "pushbullet")
    SMS = read_pool_sensor_status_values("pool_sensor_status",
                                         "notification_methods", "sms")
    if PUSHBULLET == "True" and sub_system_notifications == "True":
        send_push_notification(title,message)
    else:
        pass
    if EMAIL == "True" and sub_system_notifications == "True":
        send_email(pooldb.alert_email, title, message)
    else:
        pass
    if SMS == "True" and sub_system_notifications == "True":
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