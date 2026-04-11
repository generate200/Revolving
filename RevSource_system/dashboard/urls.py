from django.urls import path
from .views import DashboardReportView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardReportView.as_view(), name='report'),
]
