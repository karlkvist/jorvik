# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2020-05-15 11:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anagrafica', '0055_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='sede',
            name='cciaa',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Iscrizione CCIAA'),
        ),
        migrations.AddField(
            model_name='sede',
            name='rea',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Numero REA'),
        ),
        migrations.AddField(
            model_name='sede',
            name='runts',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='N. Iscrizione Registro del Volontario'),
        ),
    ]
