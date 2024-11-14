from django.urls import path
from .views import sales_report,generate_pdf_report,generate_excel_report,get_chart_data

urlpatterns = [
    path('sales-report/', sales_report, name='sales_report'),
    path('generate_pdf_report/', generate_pdf_report, name='generate_pdf_report'),
    path('generate_excel_report/', generate_excel_report, name='generate_excel_report'),
    path("get-chart-data/", get_chart_data, name="get_chart_data"),

]
