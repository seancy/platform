# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2020-04-29 02:22
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('triboo_analytics', '0007_auto_20190926_2334'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaderBoardView',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('total_score', models.PositiveIntegerField()),
                ('current_week_score', models.PositiveIntegerField()),
                ('current_month_score', models.PositiveIntegerField()),
                ('last_week_rank', models.PositiveIntegerField()),
                ('last_month_rank', models.PositiveIntegerField()),
                ('last_updated', models.DateTimeField()),
            ],
            options={
                'db_table': 'triboo_analytics_leaderboardview',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='LeaderBoard',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('first_login', models.BooleanField(default=False)),
                ('first_course_opened', models.BooleanField(default=False)),
                ('stayed_online', models.PositiveIntegerField(default=0)),
                ('non_graded_completed', models.PositiveIntegerField(default=0)),
                ('graded_completed', models.PositiveIntegerField(default=0)),
                ('unit_completed', models.PositiveIntegerField(default=0)),
                ('course_completed', models.PositiveIntegerField(default=0)),
                ('last_week_score', models.PositiveIntegerField(default=0)),
                ('last_week_rank', models.PositiveIntegerField(default=0)),
                ('last_month_score', models.PositiveIntegerField(default=0)),
                ('last_month_rank', models.PositiveIntegerField(default=0)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
