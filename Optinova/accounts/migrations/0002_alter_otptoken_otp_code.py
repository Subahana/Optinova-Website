# Generated by Django 5.1.1 on 2024-09-19 06:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otptoken',
            name='otp_code',
            field=models.CharField(default='1f98c7', max_length=6),
        ),
    ]
