#!/usr/bin/env python
# -*- coding:utf-8 -*-
import sys
sys.path.insert(0, '../..')

from gevent.event import Event
from grpc import AbsExport, RpcServer, wrap_pickle_result, DictExport, DictItemProxy

class Test(AbsExport):
    _rpc_name_ = ''
    def __init__(self, name):
        self._rpc_name_ = name
        self.name = name

    def _set_master(self, master_proxy):
        self.master = master_proxy

    def test_name(self):
        return self.name

    def test_params(self, *args, **kw):
        return (args, kw)

    def test_except(self):
        raise ValueError, 'server error test'

    @wrap_pickle_result
    def test_proxy_pickle(self):
        return self.master

    def test_proxy(self, proxy, _proxy=True):
        return proxy.get_name()

    def echo(self, msg):
        return msg

class Master(DictExport):
    _rpc_name_ = 'master'
    def __init__(self, addr):
        self.tests = dict(('item%d'%i, Test('item%d'%i)) for i in xrange(1, 11))
        self.addr = addr

    @wrap_pickle_result
    def __getitem__(self, key):
        self.tests[key]
        return DictItemProxy(self._rpc_id_, dict_name='tests', key=key, addr=self.addr)


def main():
    if sys.platform.startswith('linux'):
        endpoint = 'test.sock'
    else:
        endpoint = ('127.0.0.1', 18081)

    master = Master(endpoint)
    t1 = Test('server')
    svr = RpcServer()
    svr.bind(endpoint)
    svr.register(t1)
    svr.register(master)
    t1._set_master(svr.get_export_proxy(master))
    svr.start()
    print 'server start!'
    wait = Event()
    try:
        wait.wait()
    except KeyboardInterrupt:
        pass
    finally:
        svr.stop()


if __name__ == '__main__':
    main()
