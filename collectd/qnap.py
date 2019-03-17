from __future__ import print_function  # Python 2 compatibility
import sys

# Python 2 compatibility
try:
    ModuleNotFoundError
except NameError:
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
    'host': '192.168.1.13',
    'community': 'public',
}


def parse_cpu(value):
    percentage = value.decode('utf-8').split(' ')[0]
    return float(percentage)


def parse_hdd_temperature(value):
    celsius = value.decode('utf-8').split(' ')[0]
    return int(celsius)


def parse_hdd_size(value):
    size = value.decode('utf-8').split(' ')[0]
    return float(size)


def parse_hdd_smart(value):
    # https://www.qnap.com/en/how-to/faq/article/what-is-the-definition-of-hdd-s-m-a-r-t-status-abnormal-normal-good/
    smart_map = {
        'abnormal': -1,
        'normal': 0,
        'good': 1,
    }
    smart = 999  # unknown
    try:
        smart = smart_map[value.decode('utf-8').strip().lower()]
    except KeyError:
        pass
    return int(smart)


def _hdd_metrics_base(hdd_id):
    return {
        # hdIndex OBJECT-TYPE
        #     SYNTAX  INTEGER
        #     ACCESS  read-only
        #     STATUS  mandatory
        #     DESCRIPTION
        #             "A unique value for each hard disk.  Its value
        #             ranges between 1 and the value of IfNumber.  The
        #             value for each interface must remain constant at
        #             least from one re-initialization of the entity's
        #             network management system to the next re-
        #             initialization."
        #     ::= { hdEntry 1 }
        # e.g.: "HDDx"
        'instance': 'oid:1.3.6.1.4.1.24681.1.2.11.1.2.%s' % hdd_id,
        # hdModel OBJECT-TYPE
        #     SYNTAX  DisplayString
        #     ACCESS  read-only
        #     STATUS  mandatory
        #     DESCRIPTION "Hard disk model."
        #     ::= { hdEntry 5 }
        # e.g.: "WD40EZRX-00SPEB0\n"
        'description': 'oid:1.3.6.1.4.1.24681.1.2.11.1.5.%s' % hdd_id,
    }.copy()


def _hdd_metrics_temperature(hdd_id):
    # NAS-MIB.txt
    # hdTemperature OBJECT-TYPE
    #     SYNTAX  DisplayString
    #     ACCESS  read-only
    #     STATUS  mandatory
    #     DESCRIPTION
    #             "Hard disk temperature."
    #     ::= { hdEntry 3 }
    # e.g.: b'38 C/100 F'
    # fahrenheit = v.decode('utf-8').split('/')[1].split(' ')[0]
    meta = _hdd_metrics_base(hdd_id)
    meta.update({
        'type': 'temperature',
        'value': 'oid:1.3.6.1.4.1.24681.1.2.11.1.3.%s' % hdd_id,  # "35 C/95 F"
        'value_parse_method': parse_hdd_temperature
    })
    return meta


def _hdd_metrics_size(hdd_id):
    # NAS-MIB.txt
    # hdCapacity OBJECT-TYPE
    #     SYNTAX  DisplayString
    #     ACCESS  read-only
    #     STATUS  mandatory
    #     DESCRIPTION "Hard disk capacity."
    #     ::= { hdEntry 6 }
    # e.g: "3.64 TB"
    meta = _hdd_metrics_base(hdd_id)
    meta.update({
        'type': 'capacity',
        'description': 'size',
        'value': 'oid:1.3.6.1.4.1.24681.1.2.11.1.6.%s' % hdd_id,  # "3.64 TB"
        'value_parse_method': parse_hdd_size
    })
    return meta


def _hdd_metrics_smart(hdd_id):
    # NAS-MIB.txt
    # hdSmartInfo OBJECT-TYPE
    #     SYNTAX  DisplayString
    #     ACCESS  read-only
    #     STATUS  mandatory
    #     DESCRIPTION "Hard disk SMART information."
    #     ::= { hdEntry 7 }
    #
    #         modelName OBJECT-TYPE
    #                 SYNTAX DisplayString
    #         MAX-ACCESS read-only
    #             STATUS     current
    #         DESCRIPTION
    #                         "Model name"
    #                 ::= { systemInfo 12 }
    #         hostName OBJECT-TYPE
    #                 SYNTAX DisplayString
    #         MAX-ACCESS read-only
    #             STATUS     current
    #         DESCRIPTION
    #                         "Model name"
    #                 ::= { systemInfo 13 }
    # e.g.: "GOOD"
    meta = _hdd_metrics_base(hdd_id)
    meta.update({
        'type': 'absolute',
        'description': 'smart_status',
        'value': 'oid:1.3.6.1.4.1.24681.1.2.11.1.7.%s' % hdd_id,  # "GOOD"
        'value_parse_method': parse_hdd_smart
    })
    return meta


def _hdd_metrics_status(hdd_id):
    # NAS-MIB.txt
    # hdStatus OBJECT-TYPE
    #     SYNTAX     INTEGER {
    #         ready(0), noDisk(-5), invalid(-6), rwError(-9), unknown(-4) }
    #     ACCESS  read-only
    #     STATUS  mandatory
    #     DESCRIPTION
    #             "HDD status. 0:not availible, 1:availible."
    #     ::= { hdEntry 4 }
    meta = _hdd_metrics_base(hdd_id)
    meta.update({
        'type': 'absolute',
        'description': 'status',
        'value': 'oid:1.3.6.1.4.1.24681.1.2.11.1.4.%s' % hdd_id,
    })
    return meta


def _cpu_metrics():
    #
    # NAS-MIB.txt
    meta = {
        'type': 'percent',
        'instance': '0',
        'description': 'cpu_usage',
        'value': 'oid:1.3.6.1.4.1.24681.1.2.1.0',
        'value_parse_method': parse_cpu
    }
    return meta


WANTED_STATS = [_hdd_metrics_temperature(hdd_id) for hdd_id in range(1, 5)] + \
               [_hdd_metrics_status(hdd_id) for hdd_id in range(1, 5)] + \
               [_hdd_metrics_size(hdd_id) for hdd_id in range(1, 5)] + \
               [_hdd_metrics_smart(hdd_id) for hdd_id in range(1, 5)] + \
               [_cpu_metrics()]


def snmp_get(oid):
    # Python 2 compatibility
    host = SNMP_CONFIG['host']
    if hasattr(host, 'decode'):
        host = host.decode('utf-8')
    return puresnmp.get(host, SNMP_CONFIG['community'], oid)


def read_single(stat_meta):
    result = {'type': stat_meta['type']}

    for k in ['description', 'instance', 'value']:
        if stat_meta[k].startswith('oid:'):
            result[k] = snmp_get(stat_meta[k][4:])  # strip "oid:"
        else:
            result[k] = stat_meta[k]

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
