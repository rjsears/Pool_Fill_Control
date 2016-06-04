#!/bin/sh

## v2.4

## Part of pool_fill_control project

## https://github.com/rjsears/Pool_Fill_Control

## Simple script to setup the mode on GPIO pin where
## you want it on boot. Put in /etc/rc.local to run
## on bootup.

## This makes sure all pins are set where we want them and
## that our sprinkler relay is off when we first boot the Pi.

## This is also called on script shutdown by /etc/init.d/pool_fill_control


/usr/local/bin/gpio -g write 17 1
/usr/local/bin/gpio -g mode 17 output
/usr/local/bin/gpio -g write 5 0
/usr/local/bin/gpio -g write 13 0
/usr/local/bin/gpio -g write 21 0
/usr/local/bin/gpio -g write 16 0
/usr/local/bin/gpio -g write 12 0
/usr/local/bin/gpio -g write 11 0
