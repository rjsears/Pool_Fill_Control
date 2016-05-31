#!/usr/bin/python

## Setup our Database Connection
servername = "localhost"
username = "pool_control" # Your main MySQL admin username or username that is the exact same for both databases
password = "SomeSecretPasswordHere" # Your main MySQL admin password or password that is exact same for both databases
emoncms_db = "emoncms" # The name of your emoncms (or other) database.


# Used for Sprinkler Bypass
sprinkler_bypass = "Yes"
sprinkler_type = "Rachio"	# Timer or Rachio
rachio_url = 'curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer jhdjhf-8738783473-kfkshfks-9374873487" https://api.rach.io/1/public/device/59f8edcb-9149-42saddsadsdasd-6b7/current_schedule'

############################################################################################################################
########## Runtime checking and maximum fill times
############################################################################################################################
checktime = 60		# How often (in seconds) do we want to check the pool level? This is how often the pool_level()
			# subroutine will be run which checks the database for the pool level. We will not change the 
			# state of the pool fill valve outside of this subroutine, so don't set it to something
			# like 5 hours unless you want a flooded yard!
			
			# Each "checktime cycle" will occur at the interval you specify here.		

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

