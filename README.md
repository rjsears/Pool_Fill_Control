# Pool_Fill_Control V3.3
> Major rewrite of the code. Please see the bottom of this readme for updates!

Raspberry Pi / Arduino / Python Project to automate filling of swimming pool. Includes Flask based Web Interface.

![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/V3.3/pictures/pool_control_web_interface.jpg?raw=true)


System designed by me to automatically fill my pool when a liquid level sensor determines the pool is below a preset level. The pool is filled by opening a sprinkler valve and then monitoring the liquid level sensor until the pool is full, or a pre-set time has been reached. Also tracks and logs pool water temp, pH, ORP and filter water pressure as well as water used by the pool.

![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/V3.3/pictures/screen%202016-05-30%20at%201.52.40%20PM.jpg?raw=true)
![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/V3.3/pictures/PFC_internal.jpg?raw=true)
![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/V3.3/pictures/PFC_Internal_Connected.jpg?raw=true)
![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/V3.3/pictures/PFC_external.jpg?raw=true)



The pool can be filled automatically, or it can be filled by pressing a manual fill button.  A cutout switch on the system prevents the relay from opening the sprinkler valve in the event there is a problem with the system. 

Because our irrigation system is required to have a backfeed prevention vacuum breaker system already, I choose to connect our pool fill project to our irrigation system. Because of this, I needed a way to make sure I did not try to fill the pool while the sprinklers are running. I can check this in two ways, the first is a simple “black out timer” that you would set to the times your sprinklers run, or with an API integration with the Rachio sprinkler system (which we have).  In this case, before we fill the pool, we query the API and determine in real time if our sprinklers are running.

Because we fill the pool via existing pool water lines, I do not want to fill the pool while my pool pump is running. I monitor all electrical usage in the house utilizing OpenEnergyMonitor’s (OEM) emoncms along with hardware from both OEM as well as Brultech. This information is stored in a MySQL database. I simply query that database and see how many watts are currently being used by my pool subpanel and if it is over a certain amount, I do not allow the pool to be filled (automatically or manually).

In case of a problem with the software or hardware, I have a timer that runs anytime we are filling the pool automatically. If we go over a preset amount of time, we force the sprinkler valve closed, log the error and send a notification.
There is a manual fill button that allows me to fill the pool when I want to fill it as opposed to waiting for the automatic system to do it for me. Because it is manual, it does not care how long it will run and is not subject to the run timer. However, it is subject to the sprinkler and pump controls. 

I am not a programmer and this is just some fun stuff that I have been working on in my spare time. Eventually I will expand this to include a full monitoring system of the pool chemicals and other automation including a web interface to view all of the system parameters.

Currrently the only notifications that are included are logging and pushbullet.

V2.4 now includes 5 different system status LEDs. These include:
 - Sprinklers Running (BLUE)
 - Pool Pump Running (YELLOW) (requires some type of external power monitor)
 - System OK (GREEN)
 - System ERROR (RED)
 - Pool Filling (BLUE)
<br><br>
 
V2.5 (2016-06-04)
 - Added additional DPDT switch that physically breaks power to the sprinkler fill valve
   as well as sets notifications, resets the fill relay (if in use) and logs the event.
 - Added additional LED for the above switch to show when we have manually cut off power
   to our sprinkler fill valve.
 - Centralized all Pushbullet notifications
 - Various bug fixes

<br><br>
V2.6 (2016-06-05)
- Code Optimization
- Bug Fixes
- Added Watchdog support - if no watchdog notification every 70 seconds, script restarts
 
<br>
V2.7 (2016-06-11)
- Added Atlas Scientific pH and ORP probes to system. They are, for now, just logging to log file (logger.info).

<br>

V2.8 (2016-06-13)
- Updated how the pH and ORP probes are read.
- Added ability to log to one or more Emoncms servers, locally or remote

<br>

V2.9 (2016-06-18)
- Eliminated alerting.py file, added contents to pooldb.py file.
- Added a lot of DEBUG printing to STDOUT if DEBUG == 1 is set. 
- Moved pool_level and pump_running_watts table defs to pooldb.py
  so that you do not have to modify table definitions in main script.
- Added in temperature compensation function for pH readings if you
  have a pool water temp probe. Configuration is done in pooldb.py

<br>

V3.0 (2016-09-04)
- Added additional relay to control sprinkler transformer so it is not running 24x7.
- Added new function to control both relays. 
- Added addition debug and logging messages.

V3.1 (2016-10-08)
- Added new sensor checking function to check that our temp and
  pool level sensors are responding as required and included
  notifications if they exceed a certain number of timeouts
  or their battery voltage drops too low. Also updated pool
  fill to stop automatically if we lose communication with 
  with our pool level sensor.

- Updated pool_fill() to include calls to differnt functions
  to streamline that particular function. Also cuts down on
  a couple of global variables. Need to continue to clean
  this up as I go through and optimize the code. 

- Changed the way we get the pool level. We used to have a 0
  or a 1 programmed to be sent directly from the sensor. We
  would then make a decision to fill the pool based on the 
  reading from the sensor. Now I output the actual resistance
  from the sensor to the database and using these values we 
  can change the level of when we want to fill the pool 
  within pooldb.py instead of having to physically reflash
  the pool_level arduino sensor.

V3.2 (Unpublished)

V3.3 (2018-02-20)
- Major rewrite of code. Instead of a very large, nearly monolithic threaded
  application, I rewrote the code into various parts. The first part is a
  threaded application that does nothing more than to watch for physical
  button presses on the pool control console and does an action based on what
  button has been pressed. The second part is a cron based application that
  does all of the sensor checking and data gathering and fills the pool when
  necessary.
  
- Flask web frontend (V1) completed. Basic implementation of a Flask framework
  and web frontend that allows viewing of all of the pool parameters like
  temperature, pool water level, pH, Orp, pump watts in use, battery conditions
  for the various sensors and more. It also allows for the manual filling of the
  pool as well as the stopping of an automatic fill that is already running.
  
- Added Acid level sensor and associated functions to watch the acid level in tank
  and notify us when the acid level get too low. 
 

Based on the following hardware:

-Raspberry Pi 3<br>
-LowPowerLabs MightyHat (http://lowpowerlab.com/mightyhat)<br>
-eTape Resistive Liquid Measuring tape (http://www.milonetech.com)<br>
-OpenEnergyMonitor emonTH & emonPi (http://www.openenergymonitor.org)<br>
-Atlas Scientific USB based pH and ORP probes (http://www.atlas-scientific.com)

