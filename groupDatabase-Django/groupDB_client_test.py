from __future__ import print_function
import logging
import sys
import copy

import grpc

import groupDB_pb2
import groupDB_pb2_grpc


if __name__ == '__main__':
  logging.basicConfig()
  with grpc.insecure_channel('localhost:50051') as channel:
    stub = groupDB_pb2_grpc.databaseStub(channel)
    response = stub.addGroup(groupDB_pb2.addGroupRequest(userId = 1, groupName = "frank")
