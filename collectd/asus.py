import collectd
import os
import subprocess
from tempfile import NamedTemporaryFile

CONFIG = {
    'host': '192.168.1.1',
    'user': 'admin',
    'interface': 'ppp0',
    'ssh_key': None,
}


def collectd_config(config):
    for node in config.children:
        name = node.key.lower()
        if not name == 'asus':
            continue

        k = node.values[0]
        v = node.values[1]

        if k not in list(CONFIG.keys()):
            collectd.warning(
                'asus plugin: ignored unknown config setting {k} with '
                'value {v}'.format(**locals()))
            continue

        if k == 'ssh_key':
            with NamedTemporaryFile(mode='w', delete=False) as ssh_key_file:
                ssh_key_file.write(v)
                v = ssh_key_file.name

        CONFIG[k] = v
        collectd.debug('asus plugin: set config key "{k}" to "{v}"'.format(
            **locals()))

    collectd.debug('Config is {}'.format(CONFIG))


def _ssh_read_file(user, host, ssh_key, file_path):
    if not (os.path.isfile(ssh_key) and os.access(ssh_key, os.R_OK)):
        collectd.error(
            'asus plugin: not a valid SSH key file {}'.format(ssh_key))
        return None

    command = 'cat {}'.format(file_path)
    ssh_cmd = ('ssh -o KexAlgorithms=+diffie-hellman-group1-sha1 '
               '-o StrictHostKeyChecking=no '
               '-i {ssh_key} {user}@{host} -- {command}'.format(**locals()))
    try:
        collectd.debug('asus plugin: running {}'.format(ssh_cmd))
        return subprocess.check_output(ssh_cmd, shell=True)
    except subprocess.CalledProcessError as e:
        collectd.error('asus plugin: ssh error - {}'.format(e))
        return None


def _read_interface(interface, metric):
    stats = {
        'tx_bytes': '/sys/class/net/{interface}/statistics/tx_bytes',
        'rx_bytes': '/sys/class/net/{interface}/statistics/rx_bytes',
    }

    if metric not in stats.keys():
        raise ValueError('tx_or_rx must be "tx" or "rx" only')

    file_path = stats[metric].format(interface=interface)
    value = _ssh_read_file(
        CONFIG['user'], CONFIG['host'], CONFIG['ssh_key'], file_path)

    return value


def _dispatch(plugin, value, **kwargs):
    collectd_value = collectd.Values(type='total_bytes')
    collectd_value.plugin = plugin
    collectd_value.dispatch(values=[value], **kwargs)

    collectd.debug('Dispatched plugin={plugin} value={value}'.format(
        **locals()))


def collectd_read():
    for metric in ['rx_bytes', 'tx_bytes']:
        try:
            raw_value = _read_interface(CONFIG['interface'], metric)
            metric_value = int(raw_value)
        except (TypeError, ValueError):
            collectd.error(
                'asus plugin: could not convert metric {metric}({raw_value}) '
                'to int'.format(**locals()))
            continue
        _dispatch(metric, metric_value, host=CONFIG['host'])


collectd.register_config(collectd_config)
collectd.register_read(collectd_read)
