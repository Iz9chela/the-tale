# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2019-05-02 11:37
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pvp', '0003_battle1x1_matchmaker_battle_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='battle1x1',
            name='account',
        ),
        migrations.RemoveField(
            model_name='battle1x1',
            name='enemy',
        ),
        migrations.DeleteModel(
            name='Battle1x1',
        ),
    ]
