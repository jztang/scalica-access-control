# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import groups_pb2 as groups__pb2


class Groups_ManagerStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.AddMember = channel.unary_unary(
        '/groups_members.Groups_Manager/AddMember',
        request_serializer=groups__pb2.AddMemberRequest.SerializeToString,
        response_deserializer=groups__pb2.AddMemberReply.FromString,
        )
    self.RemoveMember = channel.unary_unary(
        '/groups_members.Groups_Manager/RemoveMember',
        request_serializer=groups__pb2.RemoveMemberRequest.SerializeToString,
        response_deserializer=groups__pb2.RemoveMemberReply.FromString,
        )
    self.Contains = channel.unary_unary(
        '/groups_members.Groups_Manager/Contains',
        request_serializer=groups__pb2.ContainsRequest.SerializeToString,
        response_deserializer=groups__pb2.ContainsReply.FromString,
        )
    self.AllMembers = channel.unary_unary(
        '/groups_members.Groups_Manager/AllMembers',
        request_serializer=groups__pb2.AllMembersRequest.SerializeToString,
        response_deserializer=groups__pb2.AllMembersReply.FromString,
        )
    self.DeleteGroup = channel.unary_unary(
        '/groups_members.Groups_Manager/DeleteGroup',
        request_serializer=groups__pb2.DeleteGroupRequest.SerializeToString,
        response_deserializer=groups__pb2.DeleteGroupReply.FromString,
        )


class Groups_ManagerServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def AddMember(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def RemoveMember(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Contains(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def AllMembers(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def DeleteGroup(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_Groups_ManagerServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'AddMember': grpc.unary_unary_rpc_method_handler(
          servicer.AddMember,
          request_deserializer=groups__pb2.AddMemberRequest.FromString,
          response_serializer=groups__pb2.AddMemberReply.SerializeToString,
      ),
      'RemoveMember': grpc.unary_unary_rpc_method_handler(
          servicer.RemoveMember,
          request_deserializer=groups__pb2.RemoveMemberRequest.FromString,
          response_serializer=groups__pb2.RemoveMemberReply.SerializeToString,
      ),
      'Contains': grpc.unary_unary_rpc_method_handler(
          servicer.Contains,
          request_deserializer=groups__pb2.ContainsRequest.FromString,
          response_serializer=groups__pb2.ContainsReply.SerializeToString,
      ),
      'AllMembers': grpc.unary_unary_rpc_method_handler(
          servicer.AllMembers,
          request_deserializer=groups__pb2.AllMembersRequest.FromString,
          response_serializer=groups__pb2.AllMembersReply.SerializeToString,
      ),
      'DeleteGroup': grpc.unary_unary_rpc_method_handler(
          servicer.DeleteGroup,
          request_deserializer=groups__pb2.DeleteGroupRequest.FromString,
          response_serializer=groups__pb2.DeleteGroupReply.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'groups_members.Groups_Manager', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
