# Generated by Django 5.1.1 on 2024-09-09 11:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_alter_customuser_profile_picture_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otptoken',
            name='otp_code',
            field=models.CharField(default='419fb4', max_length=6),
        ),
    ]
