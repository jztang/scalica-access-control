from __future__ import print_function
import grpc
import groups_pb2
import groups_pb2_grpc

if __name__=='__main__':
	channel = grpc.insecure_channel('localhost:50051')
	stub = groups_pb2_grpc.Groups_ManagerStub(channel)
	"""
	print(stub.AddMember(groups_pb2.AddMemberRequest(group_id='152', user_id='Liran')).result)
	print(stub.AddMember(groups_pb2.AddMemberRequest(group_id='152', user_id='Jason')).result)
	"""
	print(stub.AllMembers(groups_pb2.AddMemberRequest(group_id='152')).result)
	print(stub.Contains(groups_pb2.ContainsRequest(group_id='152', user_id='Liran')).result)
	"""
	print(stub.DeleteGroup(groups_pb2.DeleteGroupRequest(group_id='152')).result)
	print(stub.AddMember(groups_pb2.AddMemberRequest(group_id='152', user_id='Liran')).result)
	print(stub.AddMember(groups_pb2.AddMemberRequest(group_id='152', user_id='Jason')).result)
	print(stub.AllMembers(groups_pb2.AddMemberRequest(group_id='152')).result)
	print(stub.Contains(groups_pb2.ContainsRequest(group_id='152', user_id='Liran')).result)
	"""
