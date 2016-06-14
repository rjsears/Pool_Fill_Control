#!/usr/bin/python

## Setup our Database Connection
servername = "your.server.here"
username = "pool_control" # Your main MySQL admin username or username that is the exact same for both databases
password = "MySuperSecretPassword" # Your main MySQL admin password or password that is exact same for both databases
emoncms_db = "emoncms" # The name of your emoncms (or other) database.


## This is for our pH and ORP probes. This is the information needed to store our pH and ORP reading to our 
## two emoncms servers 
##
## Do we want to use or do we have the pH and ORP probes installed?
ph_probe = "Yes"   # Yes or No
ph_node = "pool_ph" # This will be the Node_ID that shows up in your inputs if logging to emoncms

orp_probe = "Yes"  # Yes or No
orp_node = "pool_orp" # This will be the Node_ID that shows up in your inputs if logging to emoncms


##Setup our emoncms servers
# Server 1 Information
emoncms_server1 = "Yes"				# Is this server active?
server1="localhost" 				# This could be an IP address, localhost, or an FQDN
emoncmspath1="emoncms" 				# This is the path, for example if you want http://www.yourdomain.com/emoncms/
                       				# you would put "emoncms" here. 
apikey1 = "97934jdf83k4jhrw83724khkjh83"	# Replace with your write key

# Server 2 Information
emoncms_server2 = "Yes"
server2="emoncms.yourdomain.com"
emoncmspath2=""
apikey2 = "97934jdf83k4jhrw83724khkjh83"	#Replace with your write key



# Used for Sprinkler Bypass
sprinkler_bypass = "Yes"
sprinkler_type = "Rachio"	# Timer or Rachio
rachio_url = 'curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer hhd7dhhd-did78772hs-sisjjsc" https://api.rach.io/1/public/device/9uhshyw66662ttsgwrqttsg/current_schedule'

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

