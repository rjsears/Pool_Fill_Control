#!/usr/bin/python
# -*- coding: utf-8 -*-

# Flask-Ask file for pool_control_web_engine Alexa Interface
# Use with templates.yaml file

__author__ = 'Richard J. Sears'
VERSION = "V3.5.0 (2019-02-16)"
# richard@sears.net



import sys
sys.path.append('/var/www/utilities')
import random
from flask import Flask, render_template
from flask_ask import Ask, statement, question, context
from use_database import update_database, read_database
from notifications_db import log_flask
from  pool_control_master_db import get_sprinkler_status, pool_fill_valve
from pooldb import alexa_max_pool_fill_time


app = Flask(__name__)
ask = Ask(app, "/pool_control")

degree_sign = '°'

@app.route("/")
def hello_world():
    return render_template("index_alexa.html")


@ask.intent("GetAllStats")
def get_pool_stats():
    pool_current_ph = read_database("pool_chemicals", "pool_current_ph")
    pool_current_orp = read_database("pool_chemicals", "pool_current_orp")
    pool_current_temp = int(float(read_database("system_status", "pool_current_temp")))
    pool_level_percentage = read_database("pool_level", "pool_level_percentage")
    total_current_solar_production = read_database("power_solar", "total_current_solar_production")
    total_current_power_import = read_database("power_solar", "total_current_power_import")
    screen = has_screen()
    msg = render_template('our_stats', temperature=pool_current_temp,
                                       ph=pool_current_ph,
                                       orp=pool_current_orp,
                                       level=pool_level_percentage,
                                       solar=total_current_solar_production,
                                       power_import=total_current_power_import)
    if screen:
        pool_pic = 'https://localhost/alexa/pool_control_2.jpg'
        return statement(msg).display_render(template='BodyTemplate3', background_image_url=pool_pic,
                                         text='<font size="5"><b>Pool Temperature: {0}{1}F<br/>Pool PH: {2}<br/>Pool ORP: {3}<br/>Water Level: {4}%<br/>Solar Production: {5} Watts<br/>Watts from APS: {6} Watts</b></font>'.format(pool_current_temp, degree_sign, pool_current_ph, pool_current_orp, pool_level_percentage, total_current_solar_production, total_current_power_import), format='RichText')
    else:
        return statement(msg)

@ask.intent("GetSolarOutput")
def get_solar_output():
#    log_flask("INFO", "Device ID: {}".format(context.System.device.supportedInterfaces.Display))
    total_current_solar_production = read_database("power_solar", "total_current_solar_production")
    total_current_power_import = read_database("power_solar", "total_current_power_import")
    screen = has_screen()
    if screen:
        solar_pic = 'https://localhost/alexa/solar_output.jpg'
        msg = render_template('solar_output', solar=total_current_solar_production, power_import=total_current_power_import)
        return statement(msg).display_render(template='BodyTemplate3', title='Solar Plant Output', background_image_url=solar_pic,
                                             text='<font size="5"><b>Solar Production: {0} Watts<br/>Watts from APS: {1} '
                                                  'Watts</b></font>'.format(
                                                 total_current_solar_production, total_current_power_import), format='RichText')
    else:
        return statement('Our solar system is currently producing %s watts ... and we are importing %s watts from A P S' % (
            total_current_solar_production, total_current_power_import))


@ask.intent("GetPoolTemp")
def get_pool_temp():
    pool_current_temp = read_database("system_status", "pool_current_temp")
    return statement ('Your Pool Temperature is: %s degrees' % pool_current_temp).simple_card(title='Pool Temperature', content='Your pool temperature is %s' % pool_current_temp)

@ask.intent("GetPoolPH")
def get_pool_ph():
    pool_current_ph = read_database("pool_chemicals", "pool_current_ph")
    return statement ('Your Pool P H is %s' % pool_current_ph)

@ask.intent("GetPoolORP")
def get_pool_orp():
    pool_current_orp = read_database("pool_chemicals", "pool_current_orp")
    return statement ('Your Pool Oxygen reduction potential is: %s' % pool_current_orp)

@ask.intent("GetPoolLevel")
def get_pool_level():
    pool_level_percentage = read_database("pool_level", "pool_level_percentage")
    return statement ('Your Pool water level is %s percent' % pool_level_percentage)


@ask.intent("FillPool")
def fill_pool():
    screen = has_screen()
    sprinklers_running = get_sprinkler_status()
    pool_is_filling = read_database("filling_status", "pool_is_filling")
    if pool_is_filling:
        msg = render_template('pool_already_filling')
        if screen:
            pool_filling_pic = 'https://localhost/alexa/pool_filling.jpg'
            return statement(msg).display_render(template='BodyTemplate6', background_image_url=pool_filling_pic,
                                                 text='<font size="5"><b>You pool is already filling!</b></font>',
                                                 format='RichText')
        else:
            return statement(msg)
    if sprinklers_running:
        msg = render_template('sprinklers_running')
        if screen:
            sprinkler_pic = 'https://localhost/alexa/sprinklers_running.jpg'
            return statement(msg).display_render(template='BodyTemplate6', background_image_url=sprinkler_pic,
                                                 text='<font size="5"><b>Your sprinklers are Running!</b></font>',
                                                 format='RichText')
        else:
            return statement(msg)
    else:
        msg = render_template('fill_pool', alexa_max_pool_fill_time = alexa_max_pool_fill_time)
        pool_fill_valve("ALEXA_OPEN")
        if screen:
            pool_filling_pic = 'https://localhost/alexa/pool_filling.jpg'
            return statement(msg).display_render(template='BodyTemplate6', background_image_url=pool_filling_pic,
                                                 text='<font size="5"><b>We will fill your pool for {} minutes!</b></font>'.format(alexa_max_pool_fill_time),
                                                 format='RichText')
        else:
            return statement(msg)

@ask.intent("StopFillingPool")
def stop_filling_pool():
    screen = has_screen()
    is_pool_filling = read_database("filling_status", "pool_is_filling")
    if is_pool_filling:
        gallons_current_fill = read_database("filling_gallons", "gallons_current_fill")
        pool_fill_total_time = read_database("filling_time", "pool_fill_total_time")
        msg = render_template('stop_filling', gallons_current_fill=gallons_current_fill, pool_fill_total_time=pool_fill_total_time )
        pool_fill_valve("ALEXA_CLOSE")
        if screen:
            pool_pic = 'https://localhost/alexa/pool_control_2.jpg'
            return statement(msg).display_render(template='BodyTemplate6', background_image_url=pool_pic,
                                                 text='<font size="5"><b>Filling Stopped. We added {} gallons in {} minutes.</b></font>'.format(
                                                     gallons_current_fill, pool_fill_total_time), format='RichText')
        else:
            return statement(msg)
    else:
        msg = render_template('pool_not_filling')
        if screen:
            pool_pic = 'https://localhost/alexa/pool_control_2.jpg'
            return statement(msg).display_render(template='BodyTemplate6', background_image_url=pool_pic,
                                                 text='<font size="5"><b>Your pool is not currently being filled!</b></font>', format='RichText')
        else:
            return statement(msg)



@ask.intent("CurrentGallons")
def get_current_gallons():
    screen = has_screen()
    is_pool_filling = read_database("filling_status", "pool_is_filling")
    if is_pool_filling:
        gallons_current_fill = read_database("filling_gallons", "gallons_current_fill")
        pool_fill_total_time = read_database("filling_time", "pool_fill_total_time")
        msg = render_template('current_gallons', gallons_current_fill=gallons_current_fill, pool_fill_total_time=pool_fill_total_time)
        if screen:
            pool_filling_pic = 'https://localhost/alexa/pool_filling.jpg'
            return statement(msg).display_render(template='BodyTemplate6', background_image_url=pool_filling_pic,
                                                 text='<font size="5"><b>We have added {} gallons over the last {} minutes.</b></font>'.format(
                                                     gallons_current_fill, pool_fill_total_time),
                                                 format='RichText')
        else:
            return statement(msg)
    else:
        gallons_last_fill = read_database("filling_gallons", "gallons_last_fill")
        msg = render_template('last_gallons', gallons_last_fill=gallons_last_fill)
        if screen:
            pool_pic = 'https://localhost/alexa/pool_control_2.jpg'
            return statement(msg).display_render(template='BodyTemplate6', background_image_url=pool_pic,
                                                 text='<font size="5"><b>Pool is not currently filling.<br/> Last fill gallons: {}</b></font>'.format(
                                                     gallons_last_fill), format='RichText')
        else:
            return statement(msg)




@ask.intent("OKToSwim")
def is_it_ok_to_swim(temperature):
    welcome_text = render_template('welcome')
    help_text = render_template('help')
    return question(welcome_text).reprompt(help_text)

@ask.intent("AnswerIntent", convert={'temperature': int})
def answer(temperature):
        if isinstance(temperature, int):
            pool_current_temp = int(float(read_database("system_status", "pool_current_temp")))
            if pool_current_temp < temperature:
                msg = render_template('too_cold', temperature=temperature, pool_current_temp=pool_current_temp)
            else:
                msg = render_template('just_right', temperature=temperature, pool_current_temp=pool_current_temp)
            return statement(msg)
        else: 
            msg = render_template('unknown')
            return statement(msg)

@ask.session_ended
def session_ended():
        return "{}", 200

@ask.intent('AMAZON.StopIntent')
def stop():
    return statement("Goodbye")

@ask.intent('AMAZON.CancelIntent')
def cancel():
    return statement("Goodbye")


def has_screen():
    if context.System.device.supportedInterfaces.Display is None:
        return False
    else:
        return True





if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
