from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dashboard
    path('', views.pos_dashboard, name='pos_dashboard'),
    path('sales-history/', views.sale_history, name='sale_history'),

    # Invoice management
    path('invoice/create/', views.create_invoice, name='create_invoice'),
    path('invoice/<int:invoice_id>/cart/', views.pos_cart, name='pos_cart'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoice/<int:invoice_id>/print/', views.print_receipt, name='print_receipt'),
    path('export/', views.ExportInvoicesView.as_view(), name='export_invoices'),
    path('export/sales-data/', views.ExportSalesView.as_view(), name='export_sales_data'),
    
    # API endpoints for AJAX
    path('api/invoice/<int:invoice_id>/add/', views.add_to_cart, name='add_to_cart'),
    path('api/invoice/<int:invoice_id>/line/<int:line_id>/update/', views.update_line_item, name='update_line_item'),
    path('api/invoice/<int:invoice_id>/line/<int:line_id>/remove/', views.remove_line_item, name='remove_line_item'),
    path('api/invoice/<int:invoice_id>/payment/', views.process_payment, name='process_payment'),
    path('api/products/search/', views.search_products, name='search_products'),
]
