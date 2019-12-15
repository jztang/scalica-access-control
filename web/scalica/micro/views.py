from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from .models import Following, Post, FollowingForm, PostForm, MyUserCreationForm
import grpc
import groups_pb2
import groups_pb2_grpc
import groupDB_pb2
import groupDB_pb2_grpc

import models


# Group manager RPC
channel = grpc.insecure_channel("localhost:50051")
stub = groups_pb2_grpc.Groups_ManagerStub(channel)

channel2 = grpc.insecure_channel("localhost:50052")
stub2 = groupDB_pb2_grpc.databaseStub(channel2)

# Anonymous views
#################
def index(request):
  if request.user.is_authenticated():
    return home(request)
  else:
    return anon_home(request)

def anon_home(request):
  return render(request, 'micro/public.html')



def stream(request, user_id):  
  # See if to present a 'follow' button
  form = None
  if request.user.is_authenticated() and request.user.id != int(user_id):
    try:
      f = Following.objects.get(follower_id=request.user.id,
                                followee_id=user_id)
    except Following.DoesNotExist:
      form = FollowingForm
  user = User.objects.get(pk=user_id)
  post_list = Post.objects.filter(user_id=user_id).order_by('-pub_date')

  # FILTER POSTS DEPENDING ON VISIBILITY SETTINGS

  # Filter follower-only posts
  if request.user.id != int(user_id):
    try:
      f = Following.objects.get(follower_id=request.user.id,
                                followee_id=user_id)
    except Following.DoesNotExist:
      post_list = post_list.exclude(visibility=2)

  # Filter group posts
  group_posts = post_list.filter(visibility=3)
  for post in group_posts:
    post_gid = stub2.getGroupId(groupDB_pb2.getGroupRequest(userId=post.user.id, groupName=post.group_name)).groupId

    if request.user.id != int(user_id) and stub.Contains(groups_pb2.ContainsRequest(group_id=str(post_gid), user_id=str(request.user.id))).result != 1:
      post_list = post_list.exclude(id=post.id)

  # Filter private posts
  if request.user.id != int(user_id):
    post_list = post_list.exclude(visibility=4)

  paginator = Paginator(post_list, 10)
  page = request.GET.get('page')
  try:
    posts = paginator.page(page)
  except PageNotAnInteger:
    # If page is not an integer, deliver first page.
    posts = paginator.page(1) 
  except EmptyPage:
    # If page is out of range (e.g. 9999), deliver last page of results.
    posts = paginator.page(paginator.num_pages)
  context = {
    'posts' : posts,
    'stream_user' : user,
    'form' : form,
  }
  return render(request, 'micro/stream.html', context)

def register(request):
  if request.method == 'POST':
    form = MyUserCreationForm(request.POST)
    new_user = form.save(commit=True)
    # Log in that user.
    user = authenticate(username=new_user.username,
                        password=form.clean_password2())
    if user is not None:
      login(request, user)
    else:
      raise Exception
    return home(request)
  else:
    form = MyUserCreationForm
  return render(request, 'micro/register.html', {'form' : form})

# Authenticated views
#####################
@login_required
def home(request):
  '''List of recent posts by people I follow'''
  try:
    my_post = Post.objects.filter(user=request.user).order_by('-pub_date')[0]
  except IndexError:
    my_post = None

  # Exclude the user's posts
  post_list = Post.objects.exclude(user_id=request.user.id)

  # Filter posts to people the user follows
  for post in post_list:
    try:
      f = Following.objects.get(follower_id=request.user.id,
                                followee_id=post.user.id)
    except Following.DoesNotExist:
      post_list = post_list.exclude(id=post.id)

  # FILTER POSTS DEPENDING ON VISIBILITY SETTINGS

  # Filter group posts
  group_posts = post_list.filter(visibility=3)
  for post in group_posts:
    post_gid = stub2.getGroupId(groupDB_pb2.getGroupRequest(userId=post.user.id, groupName=post.group_name)).groupId

    if stub.Contains(groups_pb2.ContainsRequest(group_id=str(post_gid), user_id=str(request.user.id))).result != 1:
      post_list = post_list.exclude(id=post.id)

  # Filter private posts
  post_list = post_list.exclude(visibility=4)

  post_list.order_by('-pub_date')[0:10]

  context = {
    'post_list': post_list,
    'my_post' : my_post,
    'post_form' : PostForm
  }
  return render(request, 'micro/home.html', context)

# Allows to post something and shows my most recent posts.
@login_required
def post(request):
  if request.method == 'POST':
    form = PostForm(request.POST)
    new_post = form.save(commit=False)
    new_post.user = request.user
    new_post.pub_date = timezone.now()
    new_post.save()
    return home(request)
  else:
    form = PostForm
  return render(request, 'micro/post.html', {'form' : form})

@login_required
def follow(request):
  if request.method == 'POST':
    form = FollowingForm(request.POST)
    new_follow = form.save(commit=False)
    new_follow.follower = request.user
    new_follow.follow_date = timezone.now()
    new_follow.save()
    return home(request)
  else:
    form = FollowingForm
  return render(request, 'micro/follow.html', {'form' : form})

@login_required
def settings(request):
  return render(request, 'micro/settings.html')

@login_required
def addGroup(request):
  #here i wanna call your method here
  with grpc.insecure_channel('localhost:50052') as channel:
    stub = groupDB_pb2_grpc.databaseStub(channel)
    stub.addGroup(groupDB_pb2.addGroupRequest(userId = request.user.id, groupName = request.POST.get('newgroup')))
    print(stub.getGroupNames(groupDB_pb2.getGroupNamesRequest(userId = request.user.id)))
  return render(request, 'micro/settings.html')


@login_required
def getGroups(request):
  #here i wanna call your method here
  with grpc.insecure_channel('localhost:50052') as channel:
    stub = groupDB_pb2_grpc.databaseStub(channel)
    groups = stub.getGroupNames(groupDB_pb2.getGroupNamesRequest(userId = request.user.id))
    print(groups)
    items = groups.split(',')
    print(items)
  return render(request, 'micro/settings.html', {'groups': groups})