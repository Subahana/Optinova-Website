# Generated by Django 5.1.1 on 2024-09-24 05:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='productvariant',
            constraint=models.UniqueConstraint(fields=('product', 'color'), name='unique_product_color'),
        ),
    ]