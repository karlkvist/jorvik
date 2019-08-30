# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2019-05-16 11:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formazione', '0037_auto_20190510_1752'),
    ]

    operations = [
        migrations.AddField(
            model_name='assenzacorsobase',
            name='esonero',
            field=models.NullBooleanField(default=False),
        ),
        migrations.AddField(
            model_name='assenzacorsobase',
            name='esonero_motivazione',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="Motivazione dell'esonero"),
        ),
    ]