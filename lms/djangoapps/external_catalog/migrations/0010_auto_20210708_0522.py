# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2021-07-08 09:22
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('external_catalog', '0009_crehanalanguage_crehanaresource'),
    ]

    operations = [
        migrations.CreateModel(
            name='AndersPinkArticle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title_id', models.IntegerField(blank=True, null=True)),
                ('title', models.TextField(null=True)),
                ('image', models.CharField(max_length=1024, null=True)),
                ('date_published', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('url', models.CharField(max_length=2048, null=True)),
                ('author', models.TextField(null=True)),
                ('reading_time', models.IntegerField(default=0, null=True)),
                ('languages', models.CharField(max_length=128, null=True)),
            ],
            options={
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='AndersPinkBriefing',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('briefing_id', models.IntegerField(blank=True, null=True)),
                ('name', models.TextField()),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='anderspinkarticle',
            name='briefing_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='external_catalog.AndersPinkBriefing'),
        ),
    ]
