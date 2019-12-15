from __future__ import print_function
import grpc
import groupDB_pb2
import groupDB_pb2_grpc

if __name__=='__main__':
    # channel2 = grpc.insecure_channel("localhost:50052")
    # stub2 = groupDB_pb2_grpc.databaseStub(channel2)

    # print(stub2.getGroupId(groupDB_pb2.getGroupRequest(userId=1, groupName="Group Name")).groupId)

    with grpc.insecure_channel('localhost:50052') as channel:
        stub = groupDB_pb2_grpc.databaseStub(channel)
        print(stub.getGroupId(groupDB_pb2.getGroupRequest(userId=1, groupName="Group Name")).groupId)