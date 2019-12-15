import redis
import grpc
import groups_pb2
import groups_pb2_grpc
from concurrent import futures
import logging

#make sure to have redis downloaded and to open them on 4 separate ports as below
redisClient_0=redis.StrictRedis(host='localhost', port=6379, db=0) #open revis server 0
redisClient_1=redis.StrictRedis(host='localhost', port=6380, db=1) #open revis server 1
redisClient_2=redis.StrictRedis(host='localhost', port=6381, db=2) #open revis server 2
redisClient_3=redis.StrictRedis(host='localhost', port=6382, db=3) #open revis server 3


#logging cofiguration to save what's happening
logging.basicConfig(filename='redis_log.txt',
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

#rpcs to do a variety of functions
class GroupManager(groups_pb2_grpc.Groups_ManagerServicer): #manager system
	#all should return 1 if correct other than allmembers
	#sharded by group_id to prevent long latency with massive groups
	def AddMember(self, request, context):
		val=int(request.group_id)%4
		logging.info('Added ' + str(request.user_id) + ' to ' + str(request.group_id) + ' in client ' + str(val))
		if (val==0):
			return groups_pb2.AddMemberReply(result=redisClient_0.sadd(request.group_id, request.user_id))
		elif (val==1):
			return groups_pb2.AddMemberReply(result=redisClient_1.sadd(request.group_id, request.user_id))
		elif (val==2):
			return groups_pb2.AddMemberReply(result=redisClient_2.sadd(request.group_id, request.user_id))
		return groups_pb2.AddMemberReply(result=redisClient_3.sadd(request.group_id, request.user_id))

	def RemoveMember(self, request, context):
		val=int(request.group_id)%4 
		logging.info('Removed ' + str(request.user_id) + ' from '  + str(request.group_id) + ' in client ' + str(val))
		if (val==0):
			return groups_pb2.RemoveMemberReply(result=redisClient_0.srem(request.group_id, request.user_id))
		elif (val==1):
			return groups_pb2.RemoveMemberReply(result=redisClient_1.srem(request.group_id, request.user_id))
		elif (val==2):
			return groups_pb2.RemoveMemberReply(result=redisClient_2.srem(request.group_id, request.user_id))
		return groups_pb2.RemoveMemberReply(result=redisClient_3.srem(request.group_id, request.user_id))

	def Contains(self, request, context):
		val=int(request.group_id)%4 
		logging.info('Checking if ' +  str(request.user_id) + ' in ' + str(request.group_id) + ' in client ' + str(val))
		if (val==0):
			return groups_pb2.ContainsReply(result=redisClient_0.sismember(request.group_id, request.user_id))
		elif (val==1):
			return groups_pb2.ContainsReply(result=redisClient_1.sismember(request.group_id, request.user_id))
		elif (val==2):
			return groups_pb2.ContainsReply(result=redisClient_2.sismember(request.group_id, request.user_id))
		return groups_pb2.ContainsReply(result=redisClient_3.sismember(request.group_id, request.user_id))

	def AllMembers(self, request, context):
		val=int(request.group_id)%4
		logging.info('Returning all members of ' + str(request.group_id) + ' in client ' + str(val))
		print ('Returning all members of ' + str(request.group_id) + ' in client ' + str(val))
		if (val==0):
			return groups_pb2.AllMembersReply(result=redisClient_0.smembers(request.group_id))
		elif (val==1):
			return groups_pb2.AllMembersReply(result=redisClient_1.smembers(request.group_id))
		elif (val==2):
			return groups_pb2.AllMembersReply(result=redisClient_2.smembers(request.group_id))
		return groups_pb2.AllMembersReply(result=redisClient_3.smembers(request.group_id))

	def DeleteGroup(self, request, context):
		val=int(request.group_id)%4 
		logging.info('Deleting group' + str(request.group_id) + ' in client ' + str(val))
		if (val==0):
			return groups_pb2.DeleteGroupReply(result=redisClient_0.delete(request.group_id))
		elif (val==1):
			return groups_pb2.DeleteReply(result=redisClient_1.delete(request.group_id))
		elif (val==2):
			return groups_pb2.DeleteReply(result=redisClient_2.delete(request.group_id))
		return groups_pb2.DeleteReply(result=redisClient_3.delete(request.group_id))



def serve(): #serve def to execute and wait for termination
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	groups_pb2_grpc.add_Groups_ManagerServicer_to_server(GroupManager(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	server.wait_for_termination() #keyboard interrupt


if __name__ == "__main__":
	serve()