# Generated by Django 5.1.1 on 2024-10-10 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon_management', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coupon',
            name='discount',
        ),
        migrations.AddField(
            model_name='coupon',
            name='coupon_type',
            field=models.CharField(choices=[('percentage', 'Percentage Discount'), ('fixed', 'Fixed Amount Discount')], default='percentage', max_length=20),
        ),
        migrations.AddField(
            model_name='coupon',
            name='discount_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='coupon',
            name='discount_percentage',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
