# Generated by Django 5.1.1 on 2024-09-28 07:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_management', '0003_order_cancelled_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='cancellation_reason',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
