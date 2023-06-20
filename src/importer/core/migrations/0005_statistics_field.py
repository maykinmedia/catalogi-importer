# Generated by Django 2.2.17 on 2021-02-11 12:21

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_job_results"),
    ]

    operations = [
        migrations.RenameField(
            model_name="job",
            old_name="results",
            new_name="statistics",
        ),
        migrations.AlterField(
            model_name="job",
            name="statistics",
            field=django.contrib.postgres.fields.jsonb.JSONField(
                blank=True, default=dict, verbose_name="Statistics"
            ),
        ),
    ]
