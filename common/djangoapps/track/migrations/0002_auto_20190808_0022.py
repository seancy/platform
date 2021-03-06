# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-08-08 04:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('track', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trackinglog',
            name='section',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='trackinglog',
            name='time_spent',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='trackinglog',
            name='user_id',
            field=models.PositiveIntegerField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='trackinglog',
            name='time',
            field=models.DateTimeField(db_index=True, verbose_name=b'event time'),
        ),
        migrations.AlterIndexTogether(
            name='trackinglog',
            index_together=set([('user_id', 'section')]),
        ),
    ]
