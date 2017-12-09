#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collects temperature data from w1 sensors and store to InfluxDB.

Usage: influx-temperature.py [-m <file>] [-i <file>] [-d] [-vv]

Options:
    -m <file>      Read sensor metadata from yaml file [default: sensors.yaml].
    -i <file>      InfluxDB configuration file [default: influxdb-config.yaml].
    -v, --verbose  Verbose output.
    -d, --daemon   Run script in the background.
    -h, --help     Print help.

If a metadata file is found, the provided attributes will be stored in the
record along with the sensor identifier and temperature reading. Attributes
named 'sensor_id' and 'temperature' are ignored.

If a 'scale' attribute is provided with a value of either 'c(elsius)',
'f(ahrenheit)' or 'k(elvin)', the temperature reading for the sensor is stored
in the requested scale.

Sensor metadata file format:
---
sensor_id:
  tag_name: tag_value
  other_tag_name: other_tag

e.g.:
---
011551c3b1ff:
  location: 'bedroom 1'
021451a1c7ff
  location: 'living room'
  scale: k

"""
import copy
import datetime
import logging
import os
import pprint
import sys
import time
import yaml

from docopt import docopt
from influxdb import InfluxDBClient

log = logging.getLogger(__name__)


def initialise_w1thermsensor():
    os.environ['W1THERMSENSOR_NO_KERNEL_MODULE'] = '1'
    from w1thermsensor.errors import KernelModuleLoadError
    del os.environ['W1THERMSENSOR_NO_KERNEL_MODULE']

    try:
        import w1thermsensor
        w1thermsensor.core.load_kernel_modules()
        return w1thermsensor.W1ThermSensor()
    except KernelModuleLoadError:
        log.error('Module w1thermsensor could not load required kernel '
                  'modules. Run as root or load them yourself.')
        return None


def validate_metadata_is_reserved(sensor_id, meta_name):
    reserved_words = ['sensor_id', 'temperature']
    for word in reserved_words:
        if meta_name == word:
            log.warning('Sensor "{sensor_id}" uses reserved word "{word}"; '
                        'ignoring attribute.'.format(**locals()))
            return True

    return False


def validate_metadata(sensors):
    validated_metadata = copy.deepcopy(sensors)
    for sensor_id, metadata in sensors.items():
        if not isinstance(metadata, dict):
            del validated_metadata[sensor_id]
            log.warning('No metadata defined for sensor "{sensor_id}"; ignoring '
                        'entry.'.format(**locals()))
            continue

        for meta_name, meta_value in metadata.items():
            if validate_metadata_is_reserved(sensor_id, meta_name):
                del validated_metadata[sensor_id][meta_name]

            if not validated_metadata[sensor_id]:
                del validated_metadata[sensor_id]
                log.warning('Sensor "{sensor_id}" contains no valid medatada; '
                            'ignoring entry.'.format(**locals()))

    return validated_metadata


def read_sensor_metadata(filename):
    sensor_metadata = {}
    try:
        with open(filename, 'r') as fh:
            sensor_metadata = yaml.load(fh)
    except IOError:
        log.warning('Could not read sensor metadata from {}; '
                    'ignoring.'.format(filename))
        return sensor_metadata

    return validate_metadata(sensor_metadata)


def set_logging(verbosity):
    if verbosity == 0:
        logging.basicConfig(level=logging.WARNING)
    elif verbosity == 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)


def influxdb_client(config_filename):
    kwargs = {}
    try:
        with open(config_filename, 'r') as fh:
            kwargs = yaml.load(fh)
    except IOError:
        log.info('Could not read InfluxDB configuration from {}'.format(
            config_filename))

    log.debug('Connecting to InfluxDB with: "{}"'.format(
        pprint.pformat(kwargs)))
    client = InfluxDBClient(**kwargs)
    database = kwargs.get('database', 'temperature')
    log.debug('Creating and switching to database "{}"'.format(database))
    client.create_database(database)
    client.switch_database(database)

    return client


def _temperature_in_scale(temperatures_cfk, scale):
    scale = scale or 'c'
    if scale.lower().startswith('c'):
        temperature = temperatures_cfk[0]
    elif scale.lower().startswith('f'):
        temperature = temperatures_cfk[1]
    elif scale.lower().startswith('k'):
        temperature = temperatures_cfk[2]
    else:
        log.info('Unknown temperature scale "{scale}"; '
                 'using Celsius.'.format(**locals()))
        temperature = temperatures_cfk[0]

    return temperature


def _measurement_add_tags(tags, metadata):
    for meta_name, meta_value in metadata.items():
        tags.update({meta_name: meta_value})


def new_measurement(sensor_id, metadata, temp_all_units):
    temperature = _temperature_in_scale(temp_all_units, metadata.get('scale'))
    measurement = {
        'measurement': 'temperature',
        'tags': {
            'sensor_id': sensor_id,
        },
        'time': datetime.datetime.now().isoformat(),
        'fields': {
            'temperature': temperature,
        }
    }

    _measurement_add_tags(measurement['tags'], metadata)
    log.info('Got measurement: "{}"'.format(pprint.pformat(measurement)))

    return measurement


def temperature_collection_loop(w1client, all_metadata, influx):
    while True:
        measurements = []
        for sensor in w1client.get_available_sensors():
            temp_all_units = sensor.get_temperatures([
                w1client.DEGREES_C,
                w1client.DEGREES_F,
                w1client.KELVIN])
            sensor_meta = all_metadata.get(sensor.id)
            body = new_measurement(sensor.id, sensor_meta, temp_all_units)
            measurements.append(body)

        influx.write_points(measurements, time_precision='s')

        time.sleep(1)


if __name__ == "__main__":
    options = docopt(__doc__)
    set_logging(options['--verbose'])

    if options['--daemon']:
        log.warning('-d is not implemented; ignoring.')

    w1_client = initialise_w1thermsensor()
    if w1_client is None:
        sys.exit(1)
    metadata = read_sensor_metadata(options['-m'])
    idb_client = influxdb_client(options['-i'])
    try:
        log.debug('Initialisation complete; entering collection loop.')
        temperature_collection_loop(w1_client, metadata, idb_client)
    except KeyboardInterrupt:
        log.info('Keyboard interrupt received; exiting.')
