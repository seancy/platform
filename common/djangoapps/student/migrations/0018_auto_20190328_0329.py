# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-03-28 07:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0017_courseenrollment_completed'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='lt_address',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Address'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_address_2',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Address 2'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_comments',
            field=models.TextField(blank=True, null=True, verbose_name=b'Comments'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_company',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Company'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_custom_country',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Custom Country'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_department',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Department'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_employee_id',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True, verbose_name=b'Employee ID'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_exempt_status',
            field=models.BooleanField(default=True, verbose_name=b'Exempt Status'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_gdpr',
            field=models.BooleanField(default=False, verbose_name=b'GDPR'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_hire_date',
            field=models.DateField(blank=True, null=True, verbose_name=b'Hire Date'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_is_tos_agreed',
            field=models.BooleanField(default=False, verbose_name=b'TOS agreed'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_job_code',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Job Code'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_job_description',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Job Description'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_learning_group',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Learning Group'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_level',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name=b'Level'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_phone_number',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Phone Number'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='lt_supervisor',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Supervisor'),
        ),
    ]
