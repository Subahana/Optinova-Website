from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.shortcuts import render
from django.utils import timezone
from order_management.models import Order
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import pandas as pd
import openpyxl
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, TruncDay
from dateutil.relativedelta import relativedelta

# --------------Sales Report---------------#

def sales_report(request):
    today = timezone.now().date()
    report_type = request.GET.get('report_type', 'daily')  # Default to daily if no type is selected
    
    # Set date ranges based on report type
    if report_type == 'daily':
        start_date = today
        end_date = today
    elif report_type == 'weekly':
        start_date = today - timedelta(days=7)
        end_date = today
    elif report_type == 'monthly':
        start_date = today - timedelta(days=30)
        end_date = today
    elif report_type == 'custom':
        # Get custom dates from user input
        start_date = request.GET.get('start_date', today - timedelta(days=30))
        end_date = request.GET.get('end_date', today)
    else:
        start_date = today - timedelta(days=30)
        end_date = today

    # Convert custom date inputs to date objects if necessary
    if isinstance(start_date, str):
        start_date = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = timezone.datetime.strptime(end_date, "%Y-%m-%d").date()

    # Fetch orders within the date range and annotate with totals
    orders = (
        Order.objects.filter(created_at__date__range=[start_date, end_date])
        .annotate(
            total_amount=Sum(F('items__price') * F('items__quantity'), output_field=DecimalField()),
            total_discount=F('coupon__discount_amount')  # Adjust based on how discounts are stored
        )
    )

    # Calculate overall report values
    total_sales_count = orders.count()
    total_order_amount = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_discount = orders.aggregate(Sum('total_discount'))['total_discount__sum'] or 0

    context = {
        'orders': orders,
        'total_sales_count': total_sales_count,
        'total_order_amount': total_order_amount,
        'total_discount': total_discount,
        'start_date': start_date,
        'end_date': end_date,
        'report_type': report_type,
    }

    return render(request, 'sales_report/sales_report.html', context)

def generate_pdf_report(request):
    # Query the necessary orders for the report
    orders = Order.objects.all()  # Adjust this query as needed

    # Create an HTTP response with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'

    # Generate the PDF
    p = canvas.Canvas(response, pagesize=letter)
    p.drawString(100, 750, "Sales Report")
    p.drawString(100, 730, "Order ID | Status | Total Amount | Discount | Date")

    # Loop through orders and add details to the PDF
    y_position = 710
    for order in orders:
        total_amount = order.total_amount()
        discount = order.coupon.discount_amount if order.coupon else 0
        line = f"{order.id} | {order.status} | {total_amount} | {discount} | {order.created_at}"
        p.drawString(100, y_position, line)
        y_position -= 20

    # Save the PDF to response
    p.showPage()
    p.save()
    return response


def generate_excel_report(request):
    # Create an Excel workbook and worksheet
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Sales Report'

    # Define headers
    headers = ['Order ID', 'Status', 'Amount', 'Discount', 'Date']
    worksheet.append(headers)

    # Fetch orders
    orders = Order.objects.all()  # Adjust query if necessary

    # Populate worksheet with order data
    for order in orders:
        created_at_naive = order.created_at.replace(tzinfo=None)  # Make datetime naive
        worksheet.append([
            order.id,
            order.status,
            order.total_amount(),
            order.coupon.discount if order.coupon else 0,  # Assuming a `discount` field exists in Coupon
            created_at_naive
        ])

    # Set up HTTP response with Excel file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=sales_report.xlsx'
    workbook.save(response)

    return response




