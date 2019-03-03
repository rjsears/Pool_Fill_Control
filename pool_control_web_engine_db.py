#!/usr/bin/python

# Flask file for pool_control_web_engine - DATABASE VERSION
# Running on port 8080 for right now statically (not via Apache) [TESTING]

__author__ = 'Richard J. Sears'
VERSION = "V3.5.1 (2019-03-02)"
# richard@sears.net

import sys
sys.path.append('/var/www/utilities')
from flask import Flask, render_template, redirect, url_for
import pool_control_button_monitor
import pool_control_master_db
from use_database import update_database, read_database
import ConfigParser


## Setup All of our LOGGING here:
config = ConfigParser.ConfigParser()

def read_logging_config(file, section, status):
    pathname = '/var/www/' + file
    config.read(pathname)
    if status == "LOGGING":
        current_status = config.getboolean(section, status)
    else:
        current_status = config.get(section, status)
    return current_status

def update_logging_config(file, section, status, value):
    pathname = '/var/www/' + file
    config.read(pathname)
    cfgfile = open(pathname, 'w')
    config.set(section, status, value)
    config.write(cfgfile)
    cfgfile.close()


app = Flask(__name__)


@app.route("/")
def pool_control():
    filter_current_psi = read_database("system_status", "filter_current_psi")
    pool_current_ph = read_database("pool_chemicals", "pool_current_ph")
    pool_current_orp = read_database("pool_chemicals", "pool_current_orp")
    current_pool_watts = read_database("pump_status", "pump_watts")
    pool_current_temp = read_database("system_status", "pool_current_temp")
    pool_temp_batt_percentage = read_database("system_status", "pool_temp_batt_percentage")
    pool_level_batt_percentage = read_database("system_status", "pool_level_batt_percentage")
    garage_temp_batt_percentage = read_database("system_status", "attic_temp_batt_percentage")
    attic_temp_batt_percentage = read_database("system_status", "garage_temp_batt_percentage")
    pool_is_filling = read_database("filling_status", "pool_is_filling")
    pool_manual_fill = read_database("filling_status", "pool_manual_fill")
    alexa_manual_fill = read_database("filling_status", "alexa_manual_fill")
    pool_level_percentage = read_database("pool_level", "pool_level_percentage")
    pool_level_sensor_ok = read_database("sensor_status", "pool_level_sensor_ok")
    pool_temp_sensor_ok = read_database("sensor_status", "pool_level_sensor_ok")
    pool_temp_sensor_humidity = read_database("system_status", "pool_temp_sensor_humidity")
    acid_level_ok = read_database("acid_level", "acid_level_ok")
    pump_run_led = read_database("led_status", "pump_run_led")
    system_run_led = read_database("led_status", "system_run_led")
    system_error_led = read_database("led_status", "system_error_led")
    sprinkler_run_led = read_database("led_status", "sprinkler_run_led")
    current_military_time = read_database("system_status", "current_military_time")
    pool_fill_total_time = read_database("filling_time", "pool_fill_total_time" )
    debug = read_database("logging", "console" )
    logging = read_logging_config("logging_config", "logging", "LOGGING")
    pushbullet = read_database("notification_methods", "pushbullet" )
    email = read_database("notification_methods", "email" )
    gallons_current_fill = read_database("filling_gallons", "gallons_current_fill" )
    gallons_last_fill = read_database("filling_gallons", "gallons_last_fill" )
    total_system_gallons = read_database("filling_gallons", "gallons_stop" )
    pump_gpm = read_database("pump_status", "pump_gpm" )
    pump_rpm = read_database("pump_status", "pump_rpm" )
    pump_control_active = read_database("pump_status", "pump_control_active" )
    sms = read_database("notification_methods", "sms" )
    total_current_power_utilization = read_database("power_solar", "total_current_power_utilization" )
    total_current_power_import = read_database("power_solar", "total_current_power_import" )
    total_current_solar_production = read_database("power_solar", "total_current_solar_production" )
    pump_program_running = read_database("pump_status", "pump_program_running" )
    pump_control_notifications = read_database("notification_settings", "pump_control_notifications")
    pump_control_software_notifications = read_database("notification_settings", "pump_control_software_notifications")
    pool_fill_notifications = read_database("notification_settings", "pool_fill_notifications")
    pool_level_sensor_notifications = read_database("notification_settings","pool_level_sensor_notifications")
    pool_temp_sensor_notifications = read_database("notification_settings","pool_temp_sensor_notifications")
    pool_filter_psi_notifications = read_database("notification_settings","pool_filter_psi_notifications")
    pool_acid_level_notifications = read_database("notification_settings", "pool_acid_level_notifications")
    pool_fill_control_reset_notifications = read_database("notification_settings", "pool_fill_control_reset_notifications")
    pool_database_notifications = read_database("notification_settings", "pool_database_notifications")
    pool_autofill_active = read_database("system_status", "pool_autofill_active")
    pool_pump_error_notifications = read_database("notification_settings", "pump_error_notifications")
    system_reset_required = read_database("reset_status", "system_reset_required")
    pool_level_sensor_humidity = read_database("system_status", "pool_level_sensor_humidity")
    pool_last_fill_date = pool_control_master_db.get_last_fill_date()
    return render_template("index_db.html", current_pool_watts = current_pool_watts,
            filter_current_psi = filter_current_psi,
            pool_current_temp = pool_current_temp,
            pool_current_ph = pool_current_ph,
            pool_current_orp = pool_current_orp,
            pool_temp_batt_percentage = pool_temp_batt_percentage,
            garage_temp_batt_percentage = garage_temp_batt_percentage,
            attic_temp_batt_percentage = attic_temp_batt_percentage,
            pool_temp_sensor_humidity  = pool_temp_sensor_humidity,
            pool_is_filling = pool_is_filling,
            pool_manual_fill = pool_manual_fill,
            pool_level_percentage = pool_level_percentage,
            acid_level_ok = acid_level_ok,
            pump_run_led = pump_run_led,
            system_run_led = system_run_led,
            system_error_led = system_error_led,
            sprinkler_run_led = sprinkler_run_led,
            current_military_time = current_military_time,
            pool_fill_total_time = pool_fill_total_time,
            debug = debug,
            logging = logging,
            pushbullet = pushbullet,
            email = email,
            sms = sms,
            gallons_current_fill = gallons_current_fill,
            gallons_last_fill = gallons_last_fill,
            total_system_gallons = total_system_gallons,
            pump_gpm = pump_gpm,
            pump_rpm = pump_rpm,
            pump_control_active = pump_control_active,
            total_current_solar_production = total_current_solar_production,
            total_current_power_import = total_current_power_import,
            total_current_power_utilization = total_current_power_utilization,
            pump_program_running = pump_program_running,
            pump_control_notifications = pump_control_notifications,
            pump_control_software_notifications = pump_control_software_notifications,
            pool_fill_notifications = pool_fill_notifications,
            pool_level_sensor_notifications = pool_level_sensor_notifications,
            pool_temp_sensor_notifications = pool_temp_sensor_notifications,
            pool_filter_psi_notifications = pool_filter_psi_notifications,
            pool_acid_level_notifications = pool_acid_level_notifications,
            pool_fill_control_reset_notifications = pool_fill_control_reset_notifications,
            pool_pump_error_notifications = pool_pump_error_notifications,
            pool_database_notifications = pool_database_notifications,
            pool_autofill_active = pool_autofill_active,
            system_reset_required = system_reset_required,
            alexa_manual_fill = alexa_manual_fill,
            pool_last_fill_date = pool_last_fill_date,
            pool_level_sensor_ok = pool_level_sensor_ok,
            pool_temp_sensor_ok=pool_temp_sensor_ok,
            pool_level_sensor_humidity = pool_level_sensor_humidity,
            pool_level_batt_percentage = pool_level_batt_percentage)


@app.route('/reset_now')
def toggle_reset():
    system_reset_required = read_database("reset_status", "system_reset_required")
    if system_reset_required:
        update_database("reset_status", "system_reset_required", False)
    else:
        update_database("reset_status", "system_reset_required", True)
    return redirect(url_for('pool_control'))


@app.route('/manual_button')
def web_button_press():
    pool_control_button_monitor.manual_fill_button_push(0,0,0)
    return redirect(url_for('pool_control'))

@app.route('/auto_fill_cancel')
def web_auto_fill_cancel():
    pool_control_master_db.pool_fill_valve("WEBCLOSE")
    return redirect(url_for('pool_control'))

@app.route('/pump_start')
def pump_start():
    pool_control_master_db.pump_control("START")
    return redirect(url_for('pool_control'))

@app.route('/pump_stop')
def pump_stop():
    pool_control_master_db.pump_control("STOP")
    update_database("pump_status", "pump_program_running", "stop")
    return redirect(url_for('pool_control'))

@app.route('/pump_control_software_stop')
def pump_control_software_stop():
    pool_control_master_db.pump_control_software("STOP")
    return redirect(url_for('pool_control'))

@app.route('/pump_control_software_start')
def pump_control_software_start():
    pool_control_master_db.pump_control_software("START")
    return redirect(url_for('pool_control'))

@app.route('/pump_program1')
def pump_program1():
    pool_control_master_db.pump_control('PROGRAM_1')
    update_database("pump_status", "pump_program_running", "program_1")
    return redirect(url_for('pool_control'))

@app.route('/pump_program2')
def pump_program2():
    pool_control_master_db.pump_control('PROGRAM_2')
    update_database("pump_status", "pump_program_running", "program_2")
    return redirect(url_for('pool_control'))

@app.route('/pump_program3')
def pump_program3():
    pool_control_master_db.pump_control('PROGRAM_3')
    update_database("pump_status", "pump_program_running", "program_3")
    return redirect(url_for('pool_control'))

@app.route('/pump_program4')
def pump_program4():
    pool_control_master_db.pump_control('PROGRAM_4')
    update_database("pump_status", "pump_program_running", "program_4")
    return redirect(url_for('pool_control'))

@app.route('/notifications_fill')
def toggle_notifications_fill():
    pool_fill_notifications = read_database("notification_settings", "pool_fill_notifications" )
    if pool_fill_notifications:
        update_database("notification_settings", "pool_fill_notifications", False)
    else:
        update_database("notification_settings", "pool_fill_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pump')
def toggle_notifications_pump():
    pump_control_notifications = read_database("notification_settings", "pump_control_notifications" )
    if pump_control_notifications:
        update_database("notification_settings", "pump_control_notifications", False)
    else:
        update_database("notification_settings", "pump_control_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pump_control_software')
def toggle_notifications_pump_control_software():
    pump_control_software_notifications = read_database("notification_settings", "pump_control_software_notifications" )
    if pump_control_software_notifications:
        update_database("notification_settings", "pump_control_software_notifications", False)
    else:
        update_database("notification_settings", "pump_control_software_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_level_sensor')
def toggle_notifications_pool_level_sensor():
    pool_level_sensor_notifications = read_database("notification_settings", "pool_level_sensor_notifications" )
    if pool_level_sensor_notifications:
        update_database("notification_settings", "pool_level_sensor_notifications", False)
    else:
        update_database("notification_settings", "pool_level_sensor_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_temp_sensor')
def toggle_notifications_pool_temp_sensor():
    pool_temp_sensor_notifications = read_database("notification_settings", "pool_temp_sensor_notifications" )
    if pool_temp_sensor_notifications:
        update_database("notification_settings", "pool_temp_sensor_notifications", False)
    else:
        update_database("notification_settings", "pool_temp_sensor_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_filter_psi')
def toggle_notifications_pool_filter_psi():
    pool_filter_psi_notifications = read_database("notification_settings", "pool_filter_psi_notifications" )
    if pool_filter_psi_notifications:
        update_database("notification_settings", "pool_filter_psi_notifications", False)
    else:
        update_database("notification_settings", "pool_filter_psi_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_acid_level')
def toggle_notifications_pool_acid_level():
    pool_acid_level_notifications = read_database("notification_settings", "pool_acid_level_notifications" )
    if pool_acid_level_notifications:
        update_database("notification_settings", "pool_acid_level_notifications", False)
    else:
        update_database("notification_settings", "pool_acid_level_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_pump_error')
def toggle_notifications_pool_pump_error():
    pool_pump_error_notifications = read_database("notification_settings", "pump_error_notifications" )
    if pool_pump_error_notifications:
        update_database("notification_settings", "pump_error_notifications", False)
    else:
        update_database("notification_settings", "pump_error_notifications", True)
    return redirect(url_for('pool_control'))


@app.route('/notifications_pool_fill_control_reset')
def toggle_notifications_pool_fill_control_reset():
    pool_fill_control_reset_notifications = read_database("notification_settings", "pool_fill_control_reset_notifications" )
    if pool_fill_control_reset_notifications:
        update_database("notification_settings", "pool_fill_control_reset_notifications", False)
    else:
        update_database("notification_settings", "pool_fill_control_reset_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_database')
def toggle_notifications_pool_database():
    pool_database_notifications = read_database("notification_settings", "pool_database_notifications" )
    if pool_database_notifications:
        update_database("notification_settings", "pool_database_notifications", False)
    else:
        update_database("notification_settings", "pool_database_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/debug')
def toggle_debug():
    debug = read_database("logging", "console" )
    if debug:
        update_database("logging", "console", False)
    else:
        update_database("logging", "console", True)
    return redirect(url_for('pool_control'))

@app.route('/logging')
def toggle_logging():
    logging = read_logging_config("logging_config", "logging", "LOGGING")
    if logging:
        update_logging_config("logging_config", "logging", "LOGGING", False)
    else:
        update_logging_config("logging_config", "logging", "LOGGING", True)
    return redirect(url_for('pool_control'))

@app.route('/pushbullet')
def toggle_pushbullet():
    pushbullet = read_database("notification_methods", "pushbullet" )
    if pushbullet:
        update_database("notification_methods", "pushbullet", False)
    else:
        update_database("notification_methods", "pushbullet", True)
    return redirect(url_for('pool_control'))

@app.route('/email')
def toggle_email():
    email = read_database("notification_methods", "email" )
    if email:
        update_database("notification_methods", "email", False)
    else:
        update_database("notification_methods", "email", True)
    return redirect(url_for('pool_control'))

@app.route('/sms')
def toggle_sms():
    sms = read_database("notification_methods", "sms" )
    if sms:
        update_database("notification_methods", "sms", False)
    else:
        update_database("notification_methods", "sms", True)
    return redirect(url_for('pool_control'))

@app.route('/pool_autofill')
def toggle_pool_autofill():
    pool_autofill_active = read_database("system_status", "pool_autofill_active" )
    if pool_autofill_active:
        update_database("system_status", "pool_autofill_active", False)
    else:
        update_database("system_status", "pool_autofill_active", True)
    return redirect(url_for('pool_control'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
