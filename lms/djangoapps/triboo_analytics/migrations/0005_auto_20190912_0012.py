# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-09-12 04:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('triboo_analytics', '0004_iltlearnerreport_org'),
    ]

    operations = [
        migrations.AlterField(
            model_name='iltlearnerreport',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('confirmed', 'Confirmed'), ('refused', 'Refused')], max_length=9),
        ),
    ]
