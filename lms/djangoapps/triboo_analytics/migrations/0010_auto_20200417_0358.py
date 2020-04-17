# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-04-17 07:58
from __future__ import unicode_literals

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import opaque_keys.edx.django.models
import triboo_analytics.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('triboo_analytics', '0009_auto_20200326_1136'),
    ]

    operations = [
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course_id', opaque_keys.edx.django.models.CourseKeyField(db_index=True, max_length=255)),
                ('badge_hash', models.CharField(db_index=True, max_length=100)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('grading_rule', models.CharField(max_length=255)),
                ('section_name', models.CharField(max_length=255)),
                ('threshold', models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(100)])),
            ],
        ),
        migrations.CreateModel(
            name='LearnerBadgeDailyReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', triboo_analytics.models.AutoCreatedField(default=triboo_analytics.models.get_day, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('score', models.FloatField(blank=True, default=0, null=True)),
                ('success', models.BooleanField(default=False)),
                ('success_date', models.DateTimeField(blank=True, default=None, null=True)),
                ('badge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='triboo_analytics.Badge')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'get_latest_by': 'created',
            },
            bases=(triboo_analytics.models.UnicodeMixin, triboo_analytics.models.ReportMixin, models.Model),
        ),
        migrations.AlterUniqueTogether(
            name='badge',
            unique_together=set([('course_id', 'badge_hash')]),
        ),
        migrations.AlterIndexTogether(
            name='badge',
            index_together=set([('course_id', 'badge_hash')]),
        ),
        migrations.AlterUniqueTogether(
            name='learnerbadgedailyreport',
            unique_together=set([('created', 'user', 'badge')]),
        ),
        migrations.AlterIndexTogether(
            name='learnerbadgedailyreport',
            index_together=set([('created', 'user', 'badge')]),
        ),
    ]
