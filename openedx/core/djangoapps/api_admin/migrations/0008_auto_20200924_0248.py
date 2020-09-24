# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-09-24 06:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_admin', '0007_delete_historical_api_records'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apiaccessrequest',
            name='reason',
            field=models.TextField(help_text='La raz\xf3n por la que este usuario quiere acceder a la API.'),
        ),
        migrations.AlterField(
            model_name='apiaccessrequest',
            name='status',
            field=models.CharField(choices=[(b'pending', 'Pendiente'), (b'denied', 'Denegada'), (b'approved', 'Aprobado')], db_index=True, default=b'pending', help_text='Estado de esta solicitud de acceso a la API', max_length=255),
        ),
        migrations.AlterField(
            model_name='apiaccessrequest',
            name='website',
            field=models.URLField(help_text='La URL del sitio web asociado con este usuario de API.'),
        ),
    ]
