#!/usr/bin/python

## MySQL Database integration Module. Holds all functions to read and update
## data for Pool Control System from MySQL database.

__author__ = 'Richard J. Sears'
VERSION = "V3.5.1 (2019-03-02)"
# richard@sears.net

import db_info
import mysql.connector
import logging.handlers
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



def read_database(table, column):
    log.info( "read_database() called with ({}, {})".format(table, column))
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
        log.warning("Failed to read record from database: {}".format(error))
        exit()
    finally:
        if(connection.is_connected()):
            connection.close


def read_database_fill(table, column):
    log.info("read_database_fill() called with ({}, {})".format(table, column))
    try:
        connection = mysql.connector.connect(user=db_info.username,
                                      password=db_info.password,
                                      host=db_info.servername,
                                      database=db_info.database)
        cursor = connection.cursor(buffered=True)
        cursor.execute(("SELECT `%s` FROM `%s` ORDER by time DESC LIMIT 1") % (column, table))
        for data in cursor:
            database_value = (data[0])
            return database_value
        cursor.close()
        connection.close()
    except Error as error :
        log.warning("Failed to read record from database: {}".format(error))
        exit()
    finally:
        if(connection.is_connected()):
            connection.close


def update_database(table,column,value):
    log.info("update_database() called with Table:{}, Column:{}, Value:{}".format(table, column, value))
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
        log.warning("Failed to UPDATE database: {}".format(error))
        exit()
    finally:
        if(connection.is_connected()):
            connection.close


def insert_database(table,column,value):
    log.info("update_database() called with Table:{}, Column:{}, Value:{}".format(table, column, value))
    try:
        connection = mysql.connector.connect(user=db_info.username,
                                      password=db_info.password,
                                      host=db_info.servername,
                                      database=db_info.database)
        cursor = connection.cursor(buffered=True)
        sql_insert = "INSERT INTO " + table + " SET " + column + " = %s"
        cursor.execute(sql_insert, (value,))
        connection.commit()
        cursor.close()
        connection.close()
    except Error as error :
        log.warning( "Failed to UPDATE database: {}".format(error))
        exit()
    finally:
        if(connection.is_connected()):
            connection.close


def read_emoncms_database(type, table):
    log.info("read_emoncms_database() called with Type: {}, Table: {})".format(type, table))
    try:
        connection = mysql.connector.connect(user=db_info.emoncms_username,
                                      password=db_info.emoncms_password,
                                      host=db_info.emoncms_servername,
                                      database=db_info.emoncms_db)
        cursor = connection.cursor(buffered=True)
        cursor.execute(("SELECT `%s` FROM `%s` ORDER by time DESC LIMIT 1") % (type, table))
        for data in cursor:
            database_value = (data[0])
            return database_value
        cursor.close()
        connection.close()
    except Error as error :
        log.warning( "Failed to read record from database: {}".format(error))
        exit()
    finally:
        if(connection.is_connected()):
            connection.close


def test_emoncms_db():
    """ Static test of read_emoncms_database() """
    data = read_emoncms_database("time", "feed_76")
    get_pool_level_sensor_time = int("%1.0f" % data)
    print("Pool LEVEL sensor last updated at: {}".format(get_pool_level_sensor_time))


def main():
    print("Not intended to be run directly.")
    print("This is the systemwide MySQL module.")
    print("It is called by other modules.")
    exit()


if __name__ == '__main__':
    main()
