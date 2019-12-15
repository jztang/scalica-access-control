from __future__ import print_function
import grpc
import groups_pb2
import groups_pb2_grpc

if __name__=='__main__':
	channel = grpc.insecure_channel('localhost:50052')
	stub = groupDB_pb2_grpc.Groups_ManagerStub(channel)

	#stub.AddMember(groups_pb2.AddMemberRequest(group_id='152', user_id='3'))
	stub.addGroup(groupDB_pb2.addGroupRequest(userId=1, groupName="Group 1"))
	stub.addGroup(groupDB_pb2.addGroupRequest(userId=1, groupName="Group 2"))
	stub.addGroup(groupDB_pb2.addGroupRequest(userId=1, groupName="Group 3"))