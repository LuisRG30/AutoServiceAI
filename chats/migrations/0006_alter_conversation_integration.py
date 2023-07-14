# Generated by Django 4.1.5 on 2023-07-14 07:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0005_alter_conversation_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="integration",
            field=models.ForeignKey(
                default=2,
                on_delete=django.db.models.deletion.CASCADE,
                to="chats.integration",
            ),
            preserve_default=False,
        ),
    ]