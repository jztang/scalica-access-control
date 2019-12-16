from django.conf.urls import include, url

from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^home/$', views.home, name='home'),
    url(r'^settings/$', views.settings, name='settings'),
    url(r'^stream/(?P<user_id>[0-9]+)/$', views.stream, name='stream'),
    url(r'^post/$', views.post, name='post'),
    url(r'^addGroup/$', views.addGroup, name='addGroup'),
    url(r'^follow/$', views.follow, name='follow'),
    url(r'^grouplist/$', views.getGroups, name='getGroups'),
    url(r'^memberlist/$', views.getMembers, name='getMembers'),
    #url(r'^grouplist/$', views.getGroups, name='getGroups'),
    url(r'^register/$', views.register, name='register'),
    url(r'^addToGroup/$', views.addMemberToGroup, name='addToGroup'),
    #url(r'^userslist/$', views.getAllUsers, name='getUsers'),
    url(r'^deleteGroup/$', views.deleteGroup, name='delete'),
    url(r'^deleteMember/$', views.deleteMember, name='deleteMember'),
    url(r'^userid/$', views.getUserId, name='deleteMember'),
    url('^', include('django.contrib.auth.urls'))
]
