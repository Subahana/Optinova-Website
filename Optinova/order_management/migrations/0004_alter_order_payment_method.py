# Generated by Django 5.1.1 on 2024-10-08 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_management', '0003_alter_order_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('COD', 'Cash on Delivery'), ('razorpay', 'Online Payment (Razorpay)')], max_length=20),
        ),
    ]