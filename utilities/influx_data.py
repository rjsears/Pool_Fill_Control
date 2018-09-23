# Module used by pool_control_master.py V3.4.6 or higher to read and write information to and from
# and influx database for various power readings. This is intended to be located in the utilities
# subdirectory.

# Last updated 2018-09-23

__author__ = 'Richard J. Sears'
PCM_VERSION = "pool_control_master.VERSION"

import sys
sys.path.append('../')
from influxdb import InfluxDBClient
import pooldb


def write_data(measurement, value):
    client = InfluxDBClient(pooldb.influx_host, pooldb.influx_port, pooldb.influx_user, pooldb.influx_password, pooldb.influx_dbname)

    json_body = [
            {
                "measurement": measurement,
                "fields": {
                    "value": value 
                }
            }
        ]

    client.write_points(json_body)

def read_energy_data(db, measurement, device):
    client = InfluxDBClient(pooldb.influx_host, pooldb.influx_port, pooldb.influx_user, pooldb.influx_password, db)
    results = client.query(("SELECT %s from %s ORDER by time DESC LIMIT 1") % (device, measurement))
    points = results.get_points()
    for item in points:
        return  item[device]


def main():
    print("Not intended to be run directly.")
    print("This is the systemwide InfluxDB module.")
    print("It is called by other modules.")
    exit()


if __name__ == '__main__':
    main()
