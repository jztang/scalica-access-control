from django.db import models


class user(models.Model):
    userNumber = models.IntegerField()

    def __str__(self):
        return str(self.userNumber)


class group(models.Model):
    groupName = models.CharField(max_length=50)
    user = models.ForeignKey(user, on_delete=models.CASCADE)

    def __str__(self):
        return self.groupName