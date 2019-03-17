from __future__ import print_function  # Python 2 compatibility
import sys

# Python 2 compatibility
try:
    ModuleNotFoundError
except:
    ModuleNotFoundError = ImportError

try:
    import puresnmp
except ModuleNotFoundError:
    print('puresnmp not found; try `pip install puresnmp`', file=sys.stderr)
    sys.exit(1)

# example collectd configuration
#
# LoadPlugin python
# <Plugin python>
#         ModulePath "/path/to/qnap.py/directory"
#         ModulePath "/path/to/python/site-packages"
#         Import "qnap"
#         <Module qnap>
#                 qnap "hostname" "my-hostname"
#                 qnap "host" "192.168.1.1"
#                 qnap "snmp_community" "public"
#                 qnap "snmp_version" "2c"
#        </Module>
# </Plugin>


# defaults are overridden by collectd configuration
SNMP_CONFIG = {
    'hostname': 'my-hostname',
    'host': '192.168.1.1',
    'community': 'public',
}


def parse_temperature(value):
    # e.g. return value from qnap: b'38 C/100 F'
    # fahrenheit = v.decode('utf-8').split('/')[1].split(' ')[0]
    celsius = value.decode('utf-8').split(' ')[0]
    return int(celsius)


def _hdd_temp_stat(hdd_id):
    return {
               'type': 'temperature',
               'instance': '1.3.6.1.4.1.24681.1.2.11.1.2.' + hdd_id,
               'description': '1.3.6.1.4.1.24681.1.2.11.1.5.' + hdd_id,
               'value': '1.3.6.1.4.1.24681.1.2.11.1.3.' + hdd_id,
               'value_parse_method': parse_temperature
    }


WANTED_STATS = [
    _hdd_temp_stat('1'),  # HDD1
    _hdd_temp_stat('2'),  # HDD2
    _hdd_temp_stat('3'),  # HDD3
    _hdd_temp_stat('4'),  # HDD4
]


def snmp_get(oid):
    # Python 2 compatibility
    host = SNMP_CONFIG['host']
    if hasattr(host, 'decode'):
        host = host.decode('utf-8')

    return puresnmp.get(host, SNMP_CONFIG['community'], oid)


def read_single(stat_meta):
    result = {'type': stat_meta['type']}

    for k in ['description', 'instance', 'value']:
        result[k] = snmp_get(stat_meta[k])

    value_parse_method = stat_meta.get('value_parse_method')
    if callable(value_parse_method):
        result['value'] = value_parse_method(result['value'])

    return result


def read_all():
    results = []
    for stat_meta in WANTED_STATS:
        result = read_single(stat_meta)
        results.append(result)

    return results


def collectd_config(config):
    for node in config.children:
        name = node.key.lower()
        if not name == 'qnap':
            continue

        k = node.values[0]
        v = node.values[1]

        if k not in list(SNMP_CONFIG.keys()):
            collectd.debug(
                'qnap_TS-412 plugin: ignored unknown config setting {k} with '
                'value {v}'.format(**locals()))
            continue

        SNMP_CONFIG[k] = v
        collectd.debug('qnap_TS-412 plugin: set config "{k}={v}"'.format(
            **locals()))


def metric_to_collectd_value(metric):
    collectd_value = collectd.Values(
        plugin='qnap',
        type=metric['type'],
        host=SNMP_CONFIG['hostname'],
        plugin_instance=metric['description'],
        type_instance=metric['instance'],
        values=[metric['value']]
    )
    return collectd_value


def collectd_read():
    for metric in read_all():
        value = metric_to_collectd_value(metric)
        value.dispatch()


try:
    import collectd
    collectd.register_config(collectd_config)
    collectd.register_read(collectd_read)
except ModuleNotFoundError:
    if __name__ == '__main__':
        print('printing stats to stdout', file=sys.stderr)
        import pprint
        pprint.pprint(read_all())
    else:
        print('collectd python module not found', file=sys.stderr)
        sys.exit(2)
