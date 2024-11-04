from django.urls import path
from .views import sales_report,generate_pdf_report,generate_excel_report

urlpatterns = [
    path('sales-report/', sales_report, name='sales_report'),
    path('generate_pdf_report/', generate_pdf_report, name='generate_pdf_report'),
    path('generate_excel_report/', generate_excel_report, name='generate_excel_report'),
]
