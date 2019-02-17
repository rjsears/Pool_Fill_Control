# Module used by pool_control_master.py V3.4.6 or higher to read and write information to and from
# and influx database for various power readings. This is intended to be located in the utilities
# subdirectory.

# Last updated 2019-02-16

__author__ = 'Richard J. Sears'
VERSION = "V3.5.0 (2019-02-16)"

import sys
sys.path.append('../')
from influxdb import InfluxDBClient
import db_info

def write_data(measurement, value):
    client = InfluxDBClient(db_info.influx_host, db_info.influx_port, db_info.influx_user, db_info.influx_password, db_info.influx_dbname)

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
    client = InfluxDBClient(db_info.influx_host, db_info.influx_port, db_info.influx_user, db_info.influx_password, db)
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
