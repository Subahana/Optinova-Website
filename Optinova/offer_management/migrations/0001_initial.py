# Generated by Django 5.1.4 on 2024-12-12 04:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_percent', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Discount Percentage')),
                ('start_date', models.DateField(blank=True, null=True, verbose_name='Start Date')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='End Date')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='products.category')),
            ],
        ),
    ]
