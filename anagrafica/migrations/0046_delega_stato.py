# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-05-25 17:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anagrafica', '0045_auto_20170211_1826'),
    ]

    operations = [
        migrations.AddField(
            model_name='delega',
            name='stato',
            field=models.CharField(choices=[('a', 'Attiva'), ('s', 'Sospesa')], db_index=True, default='a', max_length=2),
        ),
    ]
