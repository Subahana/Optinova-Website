# Generated by Django 5.1 on 2024-08-30 04:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0043_customuser_profile_picture_alter_otptoken_otp_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otptoken',
            name='otp_code',
            field=models.CharField(default='2ace46', max_length=6),
        ),
    ]
