import time, random
import collectd


def config_func(c):
    collectd.info('did some config')

def read_func():
    val = collectd.Values(type='total_bytes')
    val.plugin = 'testing123'
    val.dispatch(values=[123])
#    collectd.info('sent values {}'.format(val))

def some_init():
    collectd.warning('some info testing123')


collectd.register_init(some_init)
collectd.register_config(config_func)
collectd.register_read(read_func)

collectd.info('testing123')
collectd.debug('debug testing123')
