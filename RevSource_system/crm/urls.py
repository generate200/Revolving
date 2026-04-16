from django.urls import path
from .views import CustomerCreateView

app_name = 'crm'

urlpatterns = [
    path('customers/add/', CustomerCreateView.as_view(), name='customer_add'),
]
