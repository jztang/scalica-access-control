import copy
import grpc
import logging
import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accessControl.settings")
#from django.core.management import execute_from_command_line
django.setup()
from groupDatabase.models import user, group
from concurrent import futures


import groupDB_pb2
import groupDB_pb2_grpc
import groups_pb2
import groups_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = groups_pb2_grpc.Groups_ManagerStub(channel)


class database(groupDB_pb2_grpc.databaseServicer):

	def addGroup(self, request, context):
		
		currentUserId = request.userId
		currentGroupName = request.groupName

		#lookup 
		try:
			currentUser = user.objects.get(userNumber = currentUserId)
			filterSet = group.objects.filter(user=currentUser)
			for i in filterSet:
				if i.groupName == currentGroupName:
					return groupDB_pb2.addGroupReply(success = False)



		except user.DoesNotExist:
			currentUser = user(userNumber = currentUserId)
			currentUser.save()

		currentGroup = group(groupName = currentGroupName, user = currentUser)
		currentGroup.save()


		return groupDB_pb2.addGroupReply(success = True)

	def deleteGroup(self, request, context):

		currentUserId = request.userId
		currentGroupName = request.groupName
		print(currentGroupName)

		#lookup 
		try:
			currentUser = user.objects.get(userNumber = currentUserId)
			filterSet = group.objects.filter(user=currentUser)

		except user.DoesNotExist:
			return groupDB_pb2.deleteGroupReply(success = False)

		for i in filterSet:
			if i.groupName == currentGroupName:
				

				with grpc.insecure_channel('localhost:50051') as channel:
					stub = groups_pb2_grpc.Groups_ManagerStub(channel)
					stub.DeleteGroup(groups_pb2.DeleteGroupRequest(group_id = str(i.id)))

				i.delete()
				print("wsa able to delete")
				return groupDB_pb2.deleteGroupReply(success = True)

		return groupDB_pb2.deleteGroupReply(success = False)

	def getGroupId(self, request, context):
		currentUserId = request.userId
		currentGroupName = request.groupName
		print("current group name "+request.groupName)
		try:
			currentUser = user.objects.get(userNumber = currentUserId)
			filterSet = group.objects.filter(user=currentUser)
			#currentGroup = group.objects.get(user = currentUser, groupName = currentGroupName)
		except user.DoesNotExist:
			print("user dne")
			return groupDB_pb2.getGroupReply(groupId = 0)

		#print(user.objects.all())
		print(filterSet)
		for i in filterSet:
			if i.groupName == currentGroupName:
				returnID = i.id
				return groupDB_pb2.getGroupReply(groupId = returnID)
		print("end")
		return groupDB_pb2.getGroupReply(groupId = 0)

	def removeAll(self, request, context):
		user.objects.all().delete()
		group.objects.all().delete()
		return groupDB_pb2.removeAllReply(success = True)

	def getGroupNames(self, request, context):
		currentUserId = request.userId
		currentUser = user.objects.get(userNumber = currentUserId)
		filterSet = group.objects.filter(user=currentUser)
		listOfGroupNames = ""
		for i in filterSet:
			listOfGroupNames = listOfGroupNames + str(i.groupName) + ","
		listOfGroupNames = listOfGroupNames[0: len(listOfGroupNames) - 1]
		return groupDB_pb2.getGroupNamesReply(groupNames = listOfGroupNames)

groupIdCounter = 0

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    groupDB_pb2_grpc.add_databaseServicer_to_server(database(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
	logging.basicConfig()

	from django.core.management import execute_from_command_line

	execute_from_command_line(sys.argv)
	serve()
