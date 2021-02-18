# Generated by Django 2.2.17 on 2021-02-18 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_catalogconfig_uuid_apply"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogconfig",
            name="_cached_domein",
            field=models.CharField(
                blank=True, editable=False, max_length=5, verbose_name="domein"
            ),
        ),
        migrations.AddField(
            model_name="catalogconfig",
            name="_cached_rsin",
            field=models.CharField(
                blank=True, editable=False, max_length=9, verbose_name="rsin"
            ),
        ),
        migrations.AddField(
            model_name="catalogconfig",
            name="url",
            field=models.URLField(
                blank=True, editable=False, max_length=255, verbose_name="Cached URL"
            ),
        ),
        migrations.AlterField(
            model_name="catalogconfig",
            name="uuid",
            field=models.UUIDField(
                help_text="The UUID of the catalog in the Catalog API",
                verbose_name="UUID",
            ),
        ),
    ]
