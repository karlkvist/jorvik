# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2020-06-26 15:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ufficio_soci', '0018_auto_20190416_1051'),
    ]

    operations = [
        migrations.AlterField(
            model_name='riduzione',
            name='descrizione',
            field=models.CharField(help_text='Dicitura riportata sulle ricevute e nella causale della quota', max_length=500),
        ),
    ]
