# Generated by Django 5.1.1 on 2024-10-20 11:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon_management', '0002_remove_coupon_discount_coupon_coupon_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='usage_limit',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
