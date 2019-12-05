import redis
import grpc
import groups_pb2.py
import groups_pb2_grpc.py


redisClient=redis.StrictReids(host='localhost', port=6379, db=0) #open revis server

class GroupManager(groups_pb2_grpc.Groups_ManagerServicer): #manager system
	#all should return 1 if correct
	def AddMember(self, request, context): 
		return groups_pb2.AddMemberReply(redisClient.sadd(request.group_id, request.user_id))

	def RemoveMember(self, request, context):
		return groups_pb2.RemoveMemberReply(redisClient.srem(request.group_id, request.user_id))

	def Contains(self, request, context):
		return groups_pb2.ContainsReply(redisClient.sismember(request.group_id, request.user_id))

	def AllMembers(self, request, context):
		return groups_pb2.AllMembersReply(redisClient.smember(request.group_id))

	def DeleteGroup(self, request, context):
		return groups_pb2.DeleteGroupReply(redisClient.delete(request.group_id))



def serve(): #serve def to execute and wait for termination
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	debate_pb2_grpc.add_CandidateServicer_to_server(Candidate(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	server.wait_for_termination() #keyboard interrupt


if __name__ == '__main__':
	serve()