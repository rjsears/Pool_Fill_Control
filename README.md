# Pool_Fill_Control
Raspberry Pi / Arduino / Python Project to automate filling of swimming pool.



System designed by me to automatically fill my pool when a liquid level sensor determines the pool is below a preset level. The pool is filled by opening a sprinkler valve and then monitoring the liquid level sensor until the pool is full, or a pre-set time has been reached. 
The pool can be filled automatically, or it can be filled by pressing a manual fill button.  A cutout switch on the system prevents the relay from opening the sprinkler valve in the event there is a problem with the system. 
Because our irrigation system is required to have a backfeed prevention vacuum breaker system already, I choose to connect our pool fill project to our irrigation system. Because of this, I needed a way to make sure I did not try to fill the pool while the sprinklers are running. I can check this in two ways, the first is a simple “black out timer” that you would set to the times your sprinklers run, or with an API integration with the Rachio sprinkler system (which we have).  In this case, before we fill the pool, we query the API and determine in real time if our sprinklers are running.
Because we fill the pool via existing pool water lines, I do not want to fill the pool while my pool pump is running. I monitor all electrical usage in the house utilizing OpenEnergyMonitor’s (OEM) emoncms along with hardware from both OEM as well as Brultech. This information is stored in a MySQL database. I simply query that database and see how many watts are currently being used by my pool subpanel and if it is over a certain amount, I do not allow the pool to be filled (automatically or manually). 
In case of a problem with the software or hardware, I have a timer that runs anytime we are filling the pool automatically. If we go over a preset amount of time, we force the sprinkler valve closed, log the error and send a notification.
There is a manual fill button that allows me to fill the pool when I want to fill it as opposed to waiting for the automatic system to do it for me. Because it is manual, it does not care how long it will run and is not subject to the run timer. However, it is subject to the sprinkler and pump controls. 
I am not a programmer and this is just some fun stuff that I have been working on in my spare time. Eventually I will expand this to include a full monitoring system of the pool chemicals and other automation including a web interface to view all of the system parameters.



Based on the following hardware:
Raspberry Pi 3
LowPowerLabs MightyHat (http://lowpowerlab.com/mightyhat)
eTape Resistive Liquid Measuring tape (http://www.milonetech.com)
OpenEnergyMonitor emonTH & emonPi (http://www.openenergymonitor.org)

