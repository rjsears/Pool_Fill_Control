# Pool_Fill_Control V2.9
Raspberry Pi / Arduino / Python Project to automate filling of swimming pool.



System designed by me to automatically fill my pool when a liquid level sensor determines the pool is below a preset level. The pool is filled by opening a sprinkler valve and then monitoring the liquid level sensor until the pool is full, or a pre-set time has been reached. Also tracks and logs pool water temp, pH, ORP and filter water pressure as well as water used by the pool.

![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/master/pictures/screen%202016-05-30%20at%201.52.40%20PM.jpg?raw=true)
![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/master/pictures/PFC_internal.jpg?raw=true)
![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/master/pictures/PFC_Internal_Connected.jpg?raw=true)
![alt tag](https://github.com/rjsears/Pool_Fill_Control/blob/master/pictures/PFC_external.jpg?raw=true)



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
 

Based on the following hardware:

-Raspberry Pi 3<br>
-LowPowerLabs MightyHat (http://lowpowerlab.com/mightyhat)<br>
-eTape Resistive Liquid Measuring tape (http://www.milonetech.com)<br>
-OpenEnergyMonitor emonTH & emonPi (http://www.openenergymonitor.org)<br>
-Atlas Scientific USB based pH and ORP probes (http://www.atlas-scientific.com)

