import time, random
# import collectd
#
#
# def config_func(c):
#     collectd.info('did some config')
#
# def read_func():
#     val = collectd.Values(type='total_bytes')
#     val.plugin = 'testing123'
#     val.dispatch(values=[123])
# #    collectd.info('sent values {}'.format(val))
#
# def some_init():
#     collectd.warning('some info testing123')
#
#
# collectd.register_init(some_init)
# collectd.register_config(config_func)
# collectd.register_read(read_func)
#
# collectd.info('testing123')
# collectd.debug('debug testing123')

import re
from requests.auth import HTTPBasicAuth
from requests_html import HTMLSession

session = HTMLSession()
auth = HTTPBasicAuth('admin', 'f0d4ms3.')

r = session.get('http://192.168.1.1/cgi-bin/index2.asp', auth=auth)
r = session.get(
    'http://192.168.1.1/cgi-bin/Main_TrafficMonitor_realtime.asp', auth=auth)
id = re.findall("http_id: '(\w+)'", r.content.decode())[0]

# cookie: bw_rtab=ATM
# nwmapRefreshTime=1550372469982
session.cookies.set('bw_rtab', 'ATM')
session.cookies.set('nwmapRefreshTime', '1550372469982')

r = session.post(
    'http://192.168.1.1/cgi-bin/Main_TrafficMonitor_realtime.asp',
    data={'output': 'netdev', '_http_id': id},
    auth=auth
)
