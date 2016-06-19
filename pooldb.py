#!/usr/bin/python

## Setup our Database Connection
servername = "your.servername.here"
username = "pool_control" # Your main MySQL admin username or username that is the exact same for both databases
password = "SuperSecretPassword" # Your main MySQL admin password or password that is exact same for both databases
emoncms_db = "emoncms" # The name of your emoncms (or other) database.


# Set up some alerting so we know when the pool is getting filled up and when it is done.
PoolAlerting = "True"
pushbilletAPI = "Uhyd654.JUg786sgButEfskBgtav" # pushbullet API token (http://www.pushbullet.com)


## What is the table name for our pool_level feed?
pool_level_table = "feed_222"

## What is the table name for our pool_running_watts feed?
pump_running_watts_table = "feed_153"


## Do we have a pool water sensor and are we tracking the pool water temp? (Generally user for accurate pH readings).
temp_probe = "Yes"
temp_probe_table = "feed_149"

## This is for our pH and ORP probes. This is the information needed to store our pH and ORP reading to our 
## two emoncms servers 
##
## Do we want to use or do we have the pH and ORP probes installed?
ph_probe = "Yes"   # Yes or No
ph_node = "pool_ph" # This will be the Node_ID that shows up in your inputs if logging to emoncms
ph_probe_baud = 38400

orp_probe = "No"  # Yes or No
orp_node = "pool_orp" # This will be the Node_ID that shows up in your inputs if logging to emoncms
orp_probe_baud = 38400

## Do we have multiple emoncms servers and do we want them turned on...?
# Server 1 Information
emoncms_server1 = "Yes"
server1="emonpi" 				# This could be an IP address, localhost, or an FQDN
emoncmspath1="emoncms" 				# This is the path, for example if you want http://www.yourdomain.com/emoncms/
                       				# you would put "emoncms" here. 
apikey1 = "put_your_read_write_API_key_here"

# Server 2 Information
emoncms_server2 = "Yes"
server2="your.second.server.here"
emoncmspath2=""
apikey2 = "put_your_read_write_API_key_here"



# Used for Sprinkler Bypass
sprinkler_bypass = "Yes"	# Set this to "No" to disable all sprinkler checks
sprinkler_type = "Rachio"	# Timer or Rachio - sprinkler_bypass must be set to "Yes" for this to make any difference

# If you have a Rachio Sprinkler System, this is the curl request to get the sprinkler status. 
# You must have your own system, you must get your Auth:Bearer ID as well as you device ID
# from Rachio in order to use this subprocess.
rachio_url = 'curl -s -X  GET -H "Content-Type: application/json" -H "Authorization: Bearer put_your_auth_bearer_from_rachio_here" https://api.rach.io/1/public/device/your_device_id_goes_here/current_schedule'

############################################################################################################################
########## Runtime checking and maximum fill times
############################################################################################################################
checktime = 60		# How often (in seconds) do we want to check the pool level? This is how often the pool_level()
			# subroutine will be run which checks the database for the pool level. We will not change the 
			# state of the pool fill valve outside of this subroutine, so don't set it to something
			# like 5 hours unless you want a flooded yard!
			
			# Each "checktime cycle" will occur at the interval you specify here.		
			
#######  VERY VERY VERY IMPORTANT ####
# We now support a watchdog timer. I have set the timer for 90 seconds based on this 60 second checktime. If you change this checktime
# you MUST MUST MUST change the timer in /etc/systemd/system/pool_control.service otherwise your script will restart every
# 90 seconds!!!


##########################################################################################################################
maxruntime = 180	# What is the maximum number of checktime cycles you want to let your pool fill? For example
			# if you put 60 seconds above for checktime, and 180 here, it will be 60 seconds * 180 readings
			# which will be a total of three hours. Once this number is hit, if the pool still is not full,
			# we force the pool fill valve closed and notify you (if notification is set on) that there is
			# a problem. 

# WARNING * WARNING * WARNING => There is NO time check when running a manual fill. If you fail to shut off your manual
# fill, your pool will overflow!
############################################################################################################################


## Set the MAXIMUM idle wattage of your pool pump. If the reading is over this wattage, the pool will not fill since the
## pump would be running
max_wattage = 30 



## Do we have a MightyHat installed with an LCD screen and if so, do we want to output mesages to the LCD screen?
MightyHat = "True"

