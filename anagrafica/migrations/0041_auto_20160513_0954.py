# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-05-13 09:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anagrafica', '0042_auto_20160912_1611'),
    ]

    operations = [
        migrations.AddField(
            model_name='appartenenza',
            name='automatica',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Automatica'),
        ),
        migrations.AddField(
            model_name='estensione',
            name='automatica',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Automatica'),
        ),
        migrations.AddField(
            model_name='fototessera',
            name='automatica',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Automatica'),
        ),
        migrations.AddField(
            model_name='riserva',
            name='automatica',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Automatica'),
        ),
        migrations.AddField(
            model_name='trasferimento',
            name='automatica',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Automatica'),
        ),
    ]