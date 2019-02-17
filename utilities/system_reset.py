#!/usr/bin/python



"""This python script resets all of the database
entries and does a system reset on our pool control
system. Once you run this script, it sets a "reset"
flag in our MySQL database and the very next time
our main scripts runs (manually or via cron) then
the entire system is reset. This is done via the
check_system_status() function.
"""

__author__ = 'Richard J. Sears'
VERSION = "V3.5.0 (2019-02-16)"
# richard@sears.net

# Manager Our Imports
from notifications_db import debug, verbose_debug, log, notify
from use_database import update_database, read_database



def reset_now():
    """Set the "system_reset_required" flag in our database:
    >>> reset_now()
    System Reset has been Requested
    system_reset_required flag is now set! Please restart your system.
    """
    log("INFO", "System Reset Requested via system_reset.py")
    debug("System Reset has been Requested")
    system_reset_required = read_database("reset_status", "system_reset_required")
    if system_reset_required:
        print ("system_reset_required flag is now set! Please restart your system.")
    else:
        update_database("reset_status", "system_reset_required", True)
        print ("system_reset_required flag is now set! Please restart your system.")
    notify("pool_fill_control_reset_notifications", "System Reset Requested", "A system reset has been requested.")


if __name__ == '__main__':
    reset_now()
