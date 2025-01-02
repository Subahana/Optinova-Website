# Generated by Django 5.1.4 on 2024-12-12 04:00

import django.core.validators
import django.db.models.deletion
import order_management.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('coupon_management', '0001_initial'),
        ('products', '0001_initial'),
        ('user_profile', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(max_length=20, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_method', models.CharField(choices=[('COD', 'Cash on Delivery'), ('razorpay', 'Online Payment (Razorpay)'), ('Wallet', 'Wallet Payment')], max_length=20)),
                ('razorpay_order_id', models.CharField(blank=True, max_length=100, null=True)),
                ('razorpay_payment_id', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(max_length=20, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.CharField(editable=False, max_length=100, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_cancelled', models.BooleanField(default=False)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('cancellation_reason', models.CharField(blank=True, max_length=100, null=True)),
                ('is_returned', models.BooleanField(default=False)),
                ('return_reason', models.CharField(blank=True, max_length=255, null=True)),
                ('final_price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user_profile.address')),
                ('canceled_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='canceled_orders', to=settings.AUTH_USER_MODEL)),
                ('coupon', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='coupon_management.coupon')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('status', models.ForeignKey(default=order_management.models.OrderStatus.get_default_status, on_delete=django.db.models.deletion.CASCADE, to='order_management.orderstatus')),
                ('payment_details', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='order_management.paymentdetails')),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='order_management.order')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='products.productvariant')),
            ],
        ),
        migrations.CreateModel(
            name='OrderRefund',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('refund_reason', models.TextField(blank=True, null=True)),
                ('refunded_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='order_management.order')),
            ],
        ),
        migrations.AddField(
            model_name='paymentdetails',
            name='payment_status',
            field=models.ForeignKey(default=order_management.models.PaymentStatus.get_default_payment_status, null=True, on_delete=django.db.models.deletion.SET_NULL, to='order_management.paymentstatus'),
        ),
    ]
