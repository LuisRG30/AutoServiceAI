# Generated by Django 4.1.5 on 2023-07-14 01:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Integration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("integrated", "Integrado"),
                            ("whatsapp", "WhatsApp"),
                            ("telegram", "Telegram"),
                            ("web", "Web"),
                        ],
                        default="integrated",
                        max_length=255,
                    ),
                ),
                (
                    "telegram_token",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "whatsapp_token",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("web_token", models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.AddField(
            model_name="conversation",
            name="integration",
            field=models.OneToOneField(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="chats.integration",
            ),
            preserve_default=False,
        ),
    ]