# Generated by Django 5.1.1 on 2024-11-23 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_management', '0009_rename_order_id_gen_order_order_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='final_price',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
