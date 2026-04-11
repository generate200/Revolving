from django.views.generic import TemplateView


class DashboardReportView(TemplateView):
    template_name = 'dashboard/report.html'
