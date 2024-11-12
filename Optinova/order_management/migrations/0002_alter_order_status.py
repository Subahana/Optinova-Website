# Generated by Django 5.1.1 on 2024-11-11 06:58

import django.db.models.deletion
import order_management.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_management', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.ForeignKey(default=order_management.models.OrderStatus.get_default_status, on_delete=django.db.models.deletion.CASCADE, to='order_management.orderstatus'),
        ),
    ]
