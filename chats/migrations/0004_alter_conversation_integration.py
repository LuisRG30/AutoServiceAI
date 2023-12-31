# Generated by Django 4.1.5 on 2023-07-14 07:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0003_integration_conversation_integration"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="integration",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="chats.integration",
            ),
        ),
    ]
