from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django import forms
from django.forms import ModelForm, TextInput

class Post(models.Model):
  user = models.ForeignKey(settings.AUTH_USER_MODEL)
  visibility = models.IntegerField(default=1)
  #group_ID = models.IntegerField(default=0)
  group_name = models.CharField(max_length=256, blank=True)
  text = models.CharField(max_length=256, default="")
  pub_date = models.DateTimeField('date_posted')
  def __str__(self):
    if len(self.text) < 16:
      desc = self.text
    else:
      desc = self.text[0:16]
    return self.user.username + ':' + desc

class Following(models.Model):
  follower = models.ForeignKey(settings.AUTH_USER_MODEL,
                               related_name="user_follows")
  followee = models.ForeignKey(settings.AUTH_USER_MODEL,
                               related_name="user_followed")
  follow_date = models.DateTimeField('follow data')
  def __str__(self):
    return self.follower.username + "->" + self.followee.username

# Model Forms
class PostForm(ModelForm):
  class Meta:
    model = Post
    fields = ('text','visibility','group_name')
    VISIBILITY_CHOICES = (
      (1, "Public"),
      (2, "Followers"),
      (3, "Group"),
      (4, "Private"),
      )
    widgets = {
      'text': TextInput(attrs={'id' : 'input_post'}),
      'visibility': forms.Select(choices=VISIBILITY_CHOICES,attrs={'class': 'form-control'}),
      'group_name': TextInput()#attrs={'id' : 'input_group'})
    }

class FollowingForm(ModelForm):
  class Meta:
    model = Following
    fields = ('followee',)

class MyUserCreationForm(UserCreationForm):
  class Meta(UserCreationForm.Meta):
    help_texts = {
      'username' : '',
    }

