# Generated by Django 5.1.1 on 2024-10-20 11:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon_management', '0004_remove_coupon_usage_limit_coupon_used_by'),
        ('order_management', '0006_remove_order_coupon_remove_order_discount_amount_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='coupon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='coupon_management.coupon'),
        ),
    ]
