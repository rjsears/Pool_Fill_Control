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


/usr/local/bin/gpio -g write 17 1      	# Initially set the sprinkler relay to closed
/usr/local/bin/gpio -g mode 17 output  	# Pool Fill Valve Relay

# Setup the GPIO pins that we are going to use:
/usr/local/bin/gpio -g mode 2 input	# Manual Fill Switch
/usr/local/bin/gpio -g mode 3 input	# Pool Fill Valve Disable Button
/usr/local/bin/gpio -g mode 5 output  	# Sprinklers Running LED
/usr/local/bin/gpio -g mode 4 output 	# Pool Fill Solenoid Disabled LED
/usr/local/bin/gpio -g mode 13 output	# Pool Pump Running LED
/usr/local/bin/gpio -g mode 21 output	# System OK LED
/usr/local/bin/gpio -g mode 16 output	# System ERROR LED
/usr/local/bin/gpio -g mode 12 output	# Pool Filling LED
/usr/local/bin/gpio -g mode 11 output	# Manual Fill Switch LED



# Set all LEDs to OFF initially
/usr/local/bin/gpio -g write 5 0	# Sprinklers Running LED
/usr/local/bin/gpio -g write 4 0	# Pool Fill  Solenoid Disabled LED
/usr/local/bin/gpio -g write 13 0 	# Pool Pump Running LED0
/usr/local/bin/gpio -g write 21 0	# System OK LED	
/usr/local/bin/gpio -g write 16 0	# System ERROR LED
/usr/local/bin/gpio -g write 12 0	# Pool Filling LED
/usr/local/bin/gpio -g write 11 0	# Manual Fill Switch LED
