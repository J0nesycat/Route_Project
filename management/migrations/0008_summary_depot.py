# Generated by Django 4.2.19 on 2025-04-01 07:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0007_dailyworkforce_summary'),
    ]

    operations = [
        migrations.AddField(
            model_name='summary',
            name='depot',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='management.depot'),
        ),
    ]
