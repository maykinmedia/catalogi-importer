# Generated by Django 2.2.12 on 2021-01-21 12:36

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import importer.core.models
import importer.utils.storage


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CatalogConfig",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("url", models.URLField(max_length=255, verbose_name="Catalog URL")),
                (
                    "label",
                    models.CharField(
                        blank=True,
                        help_text="Human readable label.",
                        max_length=255,
                        verbose_name="Label",
                    ),
                ),
            ],
            options={
                "verbose_name": "Catalog configuration",
            },
        ),
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "year",
                    models.SmallIntegerField(
                        help_text="Year to import to.",
                        validators=[
                            django.core.validators.MinValueValidator(1000),
                            django.core.validators.MaxValueValidator(9999),
                        ],
                        verbose_name="Selectielijst year",
                    ),
                ),
                (
                    "source",
                    models.FileField(
                        help_text="i-Navigator XML export file.",
                        storage=importer.utils.storage.PrivateFileSystemStorage(),
                        upload_to=importer.core.models.get_job_source_file_name,
                        validators=[
                            django.core.validators.FileExtensionValidator(["xml"])
                        ],
                        verbose_name="XML File",
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("error", "Error"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=32,
                        verbose_name="State",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="Job created"
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Job started"
                    ),
                ),
                (
                    "stopped_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Job stopped"
                    ),
                ),
                (
                    "catalog",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="core.CatalogConfig",
                    ),
                ),
            ],
            options={
                "verbose_name": "Import Job",
            },
        ),
    ]