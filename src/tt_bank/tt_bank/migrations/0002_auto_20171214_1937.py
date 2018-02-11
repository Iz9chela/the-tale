# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-12-14 19:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tt_bank', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='currency',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='operation',
            name='currency',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
    ]
