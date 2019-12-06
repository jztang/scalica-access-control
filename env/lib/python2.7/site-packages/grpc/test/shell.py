#!/usr/bin/env python
# -*- coding:utf-8 -*-
import sys
sys.path.insert(0, '../..')
import grpc
endpoint = ('127.0.0.1', 18081)

def main():
    argv = sys.argv
    if len(argv) != 3:
        print 'usage:python shell.py ip port'
        addr = endpoint
    else:
        addr = (argv[1], int(argv[2]))
    client = grpc.RpcClient()
    client.connect(addr)
    client.start()
    client.svc.start_console()


if __name__ == '__main__':
    main()

