# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2019-12-15 01:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('micro', '0003_auto_20191205_1937'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='group_ID',
        ),
        migrations.AddField(
            model_name='post',
            name='group_name',
            field=models.CharField(default=b'', max_length=256),
        ),
    ]