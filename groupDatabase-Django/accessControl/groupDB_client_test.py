from __future__ import print_function
import logging
import sys
import copy

import grpc

import groupDB_pb2
import groupDB_pb2_grpc


if __name__ == '__main__':
  logging.basicConfig()
  with grpc.insecure_channel('localhost:50052') as channel:
    stub = groupDB_pb2_grpc.databaseStub(channel)
    stub.addGroup(groupDB_pb2.addGroupRequest(userId = 1, groupName = "frank"))
    stub.addGroup(groupDB_pb2.addGroupRequest(userId = 1, groupName = "groupTwo"))
    stub.addGroup(groupDB_pb2.addGroupRequest(userId = 2, groupName = "groupTwo"))
    stub.addGroup(groupDB_pb2.addGroupRequest(userId = 3, groupName = "groupTwo"))
    stub.getGroupId(groupDB_pb2.getGroupRequest(userId = 1, groupName = "groupTwo"))
    stub.deleteGroup (groupDB_pb2.deleteGroupRequest(userId = 1, groupName = "frank"))
    if sys.argv[1] == '1':
      print("client delete")
      stub.removeAll(groupDB_pb2.removeAllRequest(placeHolder = True))