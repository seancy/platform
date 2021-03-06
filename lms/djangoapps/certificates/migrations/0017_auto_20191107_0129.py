# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-11-07 06:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0016_auto_20190527_0601'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificategenerationcoursesetting',
            name='self_generation_enabled',
            field=models.BooleanField(default=False, help_text='Allow learners to generate their own certificates for the course. Enabling this does NOT affect usage of the management command used for batch certificate generation.'),
        ),
    ]
