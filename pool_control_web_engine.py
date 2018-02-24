#!/usr/bin/python

# Flask file for pool_control_web_engine

__author__ = 'Richard J. Sears'
VERSION = "V3.3.04 (2018-02-24)"
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
    current_pool_watts = read_pool_sensor_status_values("pool_sensor_status", "system_status", "pump_current_watts" )
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
    sms = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "sms" )
    return render_template("index.html", current_pool_watts = current_pool_watts, 
            filter_current_psi = filter_current_psi, 
            pool_current_temp = pool_current_temp,
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
            pool_level_batt_percentage = pool_level_batt_percentage)


@app.route('/manual_button')
def web_button_press():
    pool_control_button_monitor.manual_fill_button_push(0,0,0)
#    pool_manual_fill = read_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill")
#    if pool_manual_fill == "False":
#        pool_control_master.pool_fill_valve("MANUAL_OPEN")
#        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", True)
#    else:
#        pool_control_master.pool_fill_valve("MANUAL_CLOSE")
#        update_pool_sensor_status_values("pool_sensor_status", "filling_status", "pool_manual_fill", False)
    return redirect(url_for('pool_control'))

@app.route('/auto_fill_cancel')
def web_auto_fill_cancel():
    pool_control_master.pool_fill_valve("WEBCLOSE")
    return redirect(url_for('pool_control'))

@app.route('/debug')
def toggle_debug():
    debug = read_pool_sensor_status_values("pool_sensor_status", "notification_methods", "debug" )
  #  pool_control_master.toggle_debug()
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
   # pool_control_master.toggle_pushbullet()
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
