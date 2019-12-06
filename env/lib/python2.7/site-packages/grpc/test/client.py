#!/usr/bin/env python
# -*- coding:utf-8 -*-
import sys
sys.path.insert(0, '../..')

from gevent import sleep, spawn, joinall
from grpc import RpcClient, get_proxy_by_addr, get_rpc_by_addr

if sys.platform.startswith('linux'):
    endpoint = 'test.sock'
else:
    endpoint = ('127.0.0.1', 18081)
#    endpoint = ('10.96.130.150', 18011)
server_id = 'server'
master_id = 'master'

class Client(object):
    _rpc_name_ = 'client'
    def __init__(self):
        pass

    def get_name(self):
        return 'client'

def benchmark():
    client = RpcClient()
    client.connect(endpoint)
    client.start()
    proxy = client.svc.get_proxy(server_id)

    msg = '*' * 10
    index = [0]
    number = 10000

    def test_echo():
        rs = proxy.echo(msg)
        assert rs == msg, 'echo error'
        index[0] += 1

    import timeit
    t = timeit.timeit(test_echo, number=number)
    print 'total:%s  %s per/sec' % (t, number/float(t))
    assert index[0] == number, 'index error'
    client.stop()

def benchmark2():
    msg0 = '*' * 10
    index = [0]
    proxy_count = 90
    number = 1000
    def make_proxy(i):
        client = RpcClient()
        client.connect(endpoint)
        client.start()
        proxy = client.svc.get_proxy(server_id)
        proxy.name = '%s:%s' %(i, msg0)
        return proxy
    proxys = [make_proxy(i) for i in xrange(proxy_count)]

    def test_echo(proxy):
        rs = proxy.echo(proxy.name)#, _no_result=1)
        assert rs == proxy.name, 'echo error'
        index[0] += 1

    def test():
        tasks = [spawn(test_echo, proxy) for proxy in proxys]
        joinall(tasks)

    import timeit
    t = timeit.timeit(test, number=number)
    print 'total:%s  %s per/sec' % (t, index[0]/float(t))
    assert index[0] == number * proxy_count, 'index error'

    for p in proxys:
        p.get_service().stop()
    sleep(0.5)


def main():
    client = Client()
    server = get_proxy_by_addr(endpoint, server_id)
    print server.test_name()
    print server.test_params(1,2,3, a=1, b=2, d='*'*1024*10)
    try:
        server.test_except()
    except ValueError as e:
        print e

    master = server.test_proxy_pickle()
    item5 = master['item5']
    print item5.test_name()

    print server.test_proxy(client, _proxy=True)

    sleep(0.5)

    rpc = get_rpc_by_addr(endpoint)
    rpc.stop()

if __name__ == '__main__':
    argv = sys.argv
    if len(argv) == 1:
        main()
    elif argv[1] == 'b1':
        benchmark()
    elif argv[1] == 'b2':
        benchmark2()
else:
    print 'profile'
    benchmark2()
#benchmark2()


