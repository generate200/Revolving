from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import Customer
from .forms import CustomerForm


class CustomerCreateView(CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'crm/customer_form.html'

    def get_success_url(self):
        return self.request.GET.get('next') or reverse_lazy('sales:create_invoice')

    def form_valid(self, form):
        response = super().form_valid(form)
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        return redirect(next_url or self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '')
        return context
