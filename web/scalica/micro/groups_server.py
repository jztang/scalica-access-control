import redis
import grpc
import groups_pb2
import groups_pb2_grpc
from concurrent import futures


redisClient_0=redis.StrictRedis(host='localhost', port=6379, db=0) #open revis server 0
redisClient_1=redis.StrictRedis(host='localhost', port=6380, db=1) #open revis server 1
redisClient_2=redis.StrictRedis(host='localhost', port=6381, db=2) #open revis server 2
redisClient_3=redis.StrictRedis(host='localhost', port=6382, db=3) #open revis server 3

class GroupManager(groups_pb2_grpc.Groups_ManagerServicer): #manager system
	#all should return 1 if correct
	def AddMember(self, request, context):
		val=request.group_id%4
		if (val==0):
			return groups_pb2.AddMemberReply(redisClient_0.sadd(request.group_id, request.user_id))
		elif (val==1):
			return groups_pb2.AddMemberReply(redisClient_1.sadd(request.group_id, request.user_id))
		elif (val==2):
			return groups_pb2.AddMemberReply(redisClient_2.sadd(request.group_id, request.user_id))
		return groups_pb2.AddMemberReply(redisClient_3.sadd(request.group_id, request.user_id))

	def RemoveMember(self, request, context):
		val=request.group_id%4 
		if (val==0):
			return groups_pb2.AddMemberReply(redisClient_0.srem(request.group_id, request.user_id))
		elif (val==1):
			return groups_pb2.AddMemberReply(redisClient_1.srem(request.group_id, request.user_id))
		elif (val==2):
			return groups_pb2.AddMemberReply(redisClient_2.srem(request.group_id, request.user_id))
		return groups_pb2.AddMemberReply(redisClient_3.srem(request.group_id, request.user_id))

	def Contains(self, request, context):
		val=request.group_id%4 
		if (val==0):
			return groups_pb2.AddMemberReply(redisClient_0.sismember(request.group_id, request.user_id))
		elif (val==1):
			return groups_pb2.AddMemberReply(redisClient_1.sismember(request.group_id, request.user_id))
		elif (val==2):
			return groups_pb2.AddMemberReply(redisClient_2.sismember(request.group_id, request.user_id))
		return groups_pb2.AddMemberReply(redisClient_3.sismember(request.group_id, request.user_id))

	def AllMembers(self, request, context):
		val=request.group_id%4 
		if (val==0):
			return groups_pb2.AddMemberReply(redisClient_0.smember(request.group_id))
		elif (val==1):
			return groups_pb2.AddMemberReply(redisClient_1.smember(request.group_id))
		elif (val==2):
			return groups_pb2.AddMemberReply(redisClient_2.smember(request.group_id))
		return groups_pb2.AddMemberReply(redisClient_3.smember(request.group_id))

	def DeleteGroup(self, request, context):
		val=request.group_id%4 
		if (val==0):
			return groups_pb2.AddMemberReply(redisClient_0.delete(request.group_id))
		elif (val==1):
			return groups_pb2.AddMemberReply(redisClient_1.delete(request.group_id))
		elif (val==2):
			return groups_pb2.AddMemberReply(redisClient_2.delete(request.group_id))
		return groups_pb2.AddMemberReply(redisClient_3.delete(request.group_id))



def serve(): #serve def to execute and wait for termination
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	groups_pb2_grpc.add_Groups_ManagerServicer_to_server(GroupManager(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	server.wait_for_termination() #keyboard interrupt


if __name__ == '__main__':
	serve()