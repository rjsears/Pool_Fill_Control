#!/usr/bin/python

# Flask file for pool_control_web_engine

__author__ = 'Richard J. Sears'
VERSION = "V3.4 (2018-03-16)"
# richard@sears.net

import ConfigParser
from flask import Flask, render_template, redirect, url_for
import pool_control_button_monitor
import pool_control_master
config = ConfigParser.ConfigParser()

app = Flask(__name__)



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


@app.route("/")
def pool_control():
    filter_current_psi = read_pool_sensor_status_values("pool_sensor_status", "system_status", "filter_current_psi" )
    pool_current_ph = read_pool_sensor_status_values("pool_sensor_status", "pool_chemicals", "pool_current_ph" )
    pool_current_orp = read_pool_sensor_status_values("pool_sensor_status", "pool_chemicals", "pool_current_orp" )
    current_pool_watts = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_watts" )
    pool_current_temp = read_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_current_temp" )
    pool_temp_batt_percentage = read_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_temp_batt_percentage" )
    pool_level_batt_percentage = read_pool_sensor_status_values("pool_sensor_status", "system_status", "pool_level_batt_percentage" )
    pool_is_filling = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_is_filling" )
    pool_manual_fill = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill" )
    pool_level_percentage = read_pool_sensor_status_values("pool_sensor_status", "pool_level", "pool_level_percentage" )
    acid_level_ok = read_pool_sensor_status_values("pool_sensor_status", "acid_level", "acid_level_ok" )
    pump_run_led = read_pool_sensor_status_values("pool_sensor_status", "led_status", "pump_run_led" )
    system_run_led = read_pool_sensor_status_values("pool_sensor_status", "led_status", "system_run_led" )
    system_error_led = read_pool_sensor_status_values("pool_sensor_status", "led_status", "system_error_led" )
    sprinkler_run_led = read_pool_sensor_status_values("pool_sensor_status", "led_status", "sprinkler_run_led" )
    current_military_time = read_pool_sensor_status_values("pool_sensor_status", "system_status", "current_military_time" )
    pool_fill_total_time = read_pool_sensor_status_values("pool_sensor_status", "filling_time", "pool_fill_total_time" )
    debug = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug" )
    logging = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "logging" )
    pushbullet = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "pushbullet" )
    email = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "email" )
    gallons_current_fill = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_current_fill" )
    gallons_last_fill = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_last_fill" )
    total_system_gallons = read_pool_sensor_status_values("pool_sensor_status", "filling_gallons", "gallons_stop" )
    pump_gpm = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_gpm" )
    pump_rpm = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_rpm" )
    pump_control_active = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_control_active" )
    sms = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms" )
    total_current_power_utilization = read_pool_sensor_status_values("pool_sensor_status", "power_solar", "total_current_power_utilization" )
    total_current_power_import = read_pool_sensor_status_values("pool_sensor_status", "power_solar", "total_current_power_import" )
    total_current_solar_production = read_pool_sensor_status_values("pool_sensor_status", "power_solar", "total_current_solar_production" )
    pump_program_running = read_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running" )
    pump_control_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_notifications")
    pump_control_software_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_software_notifications")
    pool_fill_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_notifications")
    pool_level_sensor_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings","pool_level_sensor_notifications")
    pool_temp_sensor_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings","pool_temp_sensor_notifications")
    pool_filter_psi_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings","pool_filter_psi_notifications")
    pool_acid_level_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_acid_level_notifications")
    pool_fill_control_reset_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_control_reset_notifications")
    pool_database_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_database_notifications")
    return render_template("index.html", current_pool_watts = current_pool_watts, 
            filter_current_psi = filter_current_psi, 
            pool_current_temp = pool_current_temp,
            pool_current_ph = pool_current_ph,
            pool_current_orp = pool_current_orp,
            pool_temp_batt_percentage = pool_temp_batt_percentage,
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
            pool_database_notifications = pool_database_notifications,
            pool_level_batt_percentage = pool_level_batt_percentage)



@app.route('/manual_button')
def web_button_press():
    pool_control_button_monitor.manual_fill_button_push(0,0,0)
    return redirect(url_for('pool_control'))

@app.route('/auto_fill_cancel')
def web_auto_fill_cancel():
    pool_control_master.pool_fill_valve("WEBCLOSE")
    return redirect(url_for('pool_control'))

@app.route('/pump_start')
def pump_start():
    pool_control_master.pump_control("START")
    return redirect(url_for('pool_control'))

@app.route('/pump_stop')
def pump_stop():
    pool_control_master.pump_control("STOP")
    update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running", "stop")
    return redirect(url_for('pool_control'))

@app.route('/pump_control_software_stop')
def pump_control_software_stop():
    pool_control_master.pump_control_software("STOP")
    return redirect(url_for('pool_control'))

@app.route('/pump_control_software_start')
def pump_control_software_start():
    pool_control_master.pump_control_software("START")
    return redirect(url_for('pool_control'))

@app.route('/pump_program1')
def pump_program1():
    pool_control_master.pump_control('PROGRAM_1')
    update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running", "program_1")
    return redirect(url_for('pool_control'))

@app.route('/pump_program2')
def pump_program2():
    pool_control_master.pump_control('PROGRAM_2')
    update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running", "program_2")
    return redirect(url_for('pool_control'))

@app.route('/pump_program3')
def pump_program3():
    pool_control_master.pump_control('PROGRAM_3')
    update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running", "program_3")
    return redirect(url_for('pool_control'))

@app.route('/pump_program4')
def pump_program4():
    pool_control_master.pump_control('PROGRAM_4')
    update_pool_sensor_status_values("pool_sensor_status", "pump_status", "pump_program_running", "program_4")
    return redirect(url_for('pool_control'))

@app.route('/notifications_fill')
def toggle_notifications_fill():
    pool_fill_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_notifications" )
    if pool_fill_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pump')
def toggle_notifications_pump():
    pump_control_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_notifications" )
    if pump_control_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pump_control_software')
def toggle_notifications_pump_control_software():
    pump_control_software_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_software_notifications" )
    if pump_control_software_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_software_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pump_control_software_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_level_sensor')
def toggle_notifications_pool_level_sensor():
    pool_level_sensor_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_level_sensor_notifications" )
    if pool_level_sensor_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_level_sensor_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_level_sensor_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_temp_sensor')
def toggle_notifications_pool_temp_sensor():
    pool_temp_sensor_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_temp_sensor_notifications" )
    if pool_temp_sensor_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_temp_sensor_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_temp_sensor_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_filter_psi')
def toggle_notifications_pool_filter_psi():
    pool_filter_psi_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_filter_psi_notifications" )
    if pool_filter_psi_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_filter_psi_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_filter_psi_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_acid_level')
def toggle_notifications_pool_acid_level():
    pool_acid_level_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_acid_level_notifications" )
    if pool_acid_level_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_acid_level_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_acid_level_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_fill_control_reset')
def toggle_notifications_pool_fill_control_reset():
    pool_fill_control_reset_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_control_reset_notifications" )
    if pool_fill_control_reset_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_control_reset_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_fill_control_reset_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/notifications_pool_database')
def toggle_notifications_pool_database():
    pool_database_notifications = read_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_database_notifications" )
    if pool_database_notifications == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_database_notifications", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_settings", "pool_database_notifications", True)
    return redirect(url_for('pool_control'))

@app.route('/debug')
def toggle_debug():
    debug = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug" )
    if debug == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug", True)
    return redirect(url_for('pool_control'))

@app.route('/logging')
def toggle_logging():
    logging = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "logging" )
    if logging == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "logging", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "logging", True)
    return redirect(url_for('pool_control'))

@app.route('/pushbullet')
def toggle_pushbullet():
    pushbullet = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "pushbullet" )
    if pushbullet == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "pushbullet", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "pushbullet", True)
    return redirect(url_for('pool_control'))

@app.route('/email')
def toggle_email():
    email = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "email" )
    if email == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "email", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "email", True)
    return redirect(url_for('pool_control'))

@app.route('/sms')
def toggle_sms():
    sms = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms" )
    if sms == "True":
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms", False)
    else:
        update_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms", True)
    return redirect(url_for('pool_control'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
