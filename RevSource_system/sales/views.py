import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from django.contrib import messages

from .models import SalesInvoice, SalesLine, Payment, StockMovement, Sale
from .forms import SalesInvoiceForm, PaymentForm, QuickProductSearchForm
from products.models import Product, ProductVariant
from crm.models import Customer
from finance.models import Currency
from finance.utils.currency import CurrencyService


@login_required
def pos_dashboard(request):
    """Main POS dashboard - shows summary and quick actions"""
    context = {
        'total_sales_today': SalesInvoice.objects.filter(
            status='completed',
            created_at__date=timezone.now().date()
        ).count(),
        'revenue_today': sum(
            inv.total_amount for inv in SalesInvoice.objects.filter(
                status='completed',
                created_at__date=timezone.now().date()
            )
        ),
        'active_invoices': SalesInvoice.objects.filter(status='draft').count(),
    }
    return render(request, 'sales/pos_dashboard.html', context)


@login_required
def create_invoice(request):
    """Create a new invoice - main POS interface"""
    if request.method == 'POST':
        form = SalesInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            if not invoice.invoice_number:
                invoice.invoice_number = generate_invoice_number()
            invoice.total_amount = invoice.subtotal + invoice.tax_total - invoice.discount_total
            invoice.save()
            return redirect('sales:pos_cart', invoice_id=invoice.id)
    else:
        form = SalesInvoiceForm()
    
    context = {
        'form': form,
        'currencies': Currency.objects.filter(is_active=True),
    }
    return render(request, 'sales/create_invoice.html', context)


@login_required
def pos_cart(request, invoice_id):
    """Main POS cart interface with multiple input methods"""
    invoice = get_object_or_404(SalesInvoice, id=invoice_id)
    
    # Check access
    if invoice.status != 'draft':
        messages.error(request, 'Cannot modify completed invoice')
        return redirect('sales:pos_dashboard')
    
    search_form = QuickProductSearchForm()
    currency_service = CurrencyService(request)
    
    context = {
        'invoice': invoice,
        'search_form': search_form,
        'currencies': Currency.objects.filter(is_active=True),
        'selected_currency': currency_service.selected_currency,
        'payment_methods': Payment.PAYMENT_METHODS,
    }
    return render(request, 'sales/pos_cart.html', context)


@login_required
@require_http_methods(["POST"])
def add_to_cart(request, invoice_id):
    """AJAX endpoint to add product to cart"""
    try:
        invoice = get_object_or_404(SalesInvoice, id=invoice_id)
        
        if invoice.status != 'draft':
            return JsonResponse({'error': 'Invoice is not editable'}, status=400)
        
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = Decimal(str(data.get('quantity', 1)))
        variant_id = data.get('variant_id')
        
        if not product_id or quantity <= 0:
            return JsonResponse({'error': 'Invalid product or quantity'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        variant = None
        
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id)
        
        # Get or create line
        line = SalesLine.objects.filter(
            invoice=invoice,
            product=product,
            variant=variant
        ).first()
        
        if line:
            line.quantity += quantity
        else:
            line = SalesLine(
                invoice=invoice,
                product=product,
                variant=variant,
                quantity=quantity,
                unit_price=Decimal(str(data.get('unit_price', product.price)))
            )
        
        line.save()
        invoice.calculate_totals()
        
        return JsonResponse({
            'success': True,
            'line_id': line.id,
            'subtotal': str(invoice.subtotal),
            'total': str(invoice.total_amount),
            'cart_count': invoice.lines.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def update_line_item(request, invoice_id, line_id):
    """AJAX endpoint to update line item quantity or price"""
    try:
        invoice = get_object_or_404(SalesInvoice, id=invoice_id)
        line = get_object_or_404(SalesLine, id=line_id, invoice=invoice)
        
        if invoice.status != 'draft':
            return JsonResponse({'error': 'Invoice is not editable'}, status=400)
        
        data = json.loads(request.body)
        
        if 'quantity' in data:
            line.quantity = Decimal(str(data['quantity']))
        
        if 'unit_price' in data:
            line.unit_price = Decimal(str(data['unit_price']))
        
        if 'discount' in data:
            line.discount = Decimal(str(data['discount']))
        
        if 'tax' in data:
            line.tax = Decimal(str(data['tax']))
        
        line.save()
        invoice.calculate_totals()
        
        return JsonResponse({
            'success': True,
            'total_price': str(line.total_price),
            'subtotal': str(invoice.subtotal),
            'total': str(invoice.total_amount)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def remove_line_item(request, invoice_id, line_id):
    """AJAX endpoint to remove line item from cart"""
    try:
        invoice = get_object_or_404(SalesInvoice, id=invoice_id)
        line = get_object_or_404(SalesLine, id=line_id, invoice=invoice)
        
        if invoice.status != 'draft':
            return JsonResponse({'error': 'Invoice is not editable'}, status=400)
        
        line.delete()
        invoice.calculate_totals()
        
        return JsonResponse({
            'success': True,
            'subtotal': str(invoice.subtotal),
            'total': str(invoice.total_amount),
            'cart_count': invoice.lines.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
@csrf_exempt
def search_products(request, invoice_id):
    """AJAX endpoint for quick product search"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'products': []})
    
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(sku__icontains=query) |
        Q(barcode__icontains=query),
        is_active=True
    )[:20]
    
    data = [{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'barcode': p.barcode,
        'price': str(p.price),
    } for p in products]
    
    return JsonResponse({'products': data})


@login_required
@require_http_methods(["POST"])
def process_payment(request, invoice_id):
    """Process payment and complete invoice"""
    try:
        invoice = get_object_or_404(SalesInvoice, id=invoice_id)
        
        if invoice.status != 'draft':
            return JsonResponse({'error': 'Invoice not in draft status'}, status=400)
        
        if not invoice.lines.exists():
            return JsonResponse({'error': 'Invoice has no items'}, status=400)
        
        data = json.loads(request.body)
        
        with transaction.atomic():
            # Record payments
            total_paid = Decimal('0.00')
            for payment_data in data.get('payments', []):
                payment = Payment(
                    invoice=invoice,
                    method=payment_data['method'],
                    amount=Decimal(str(payment_data['amount'])),
                    reference=payment_data.get('reference', '')
                )
                payment.save()
                total_paid += payment.amount
            
            # Update invoice
            invoice.paid_amount = total_paid
            invoice.change_amount = total_paid - invoice.total_amount
            invoice.status = 'completed'
            invoice.posted_at = timezone.now()
            invoice.save()
            
            # Create stock movements
            for line in invoice.lines.all():
                StockMovement.objects.create(
                    product=line.product,
                    variant=line.variant,
                    quantity=-line.quantity,
                    movement_type='sale',
                    reference=invoice.invoice_number
                )
                
                # Update legacy Sale model
                Sale.objects.create(
                    product=line.product,
                    quantity=int(line.quantity),
                    total_price=line.total_price
                )
        
        return JsonResponse({
            'success': True,
            'invoice_number': invoice.invoice_number,
            'total': str(invoice.total_amount),
            'paid': str(total_paid),
            'change': str(invoice.change_amount)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def invoice_list(request):
    """List all invoices with filtering"""
    invoices = SalesInvoice.objects.all()
    
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    context = {
        'invoices': invoices,
        'status_choices': SalesInvoice.STATUS_CHOICES,
        'selected_status': status,
    }
    return render(request, 'sales/invoice_list.html', context)


@login_required
def invoice_detail(request, invoice_id):
    """View invoice details and receipt"""
    invoice = get_object_or_404(SalesInvoice, id=invoice_id)
    
    context = {
        'invoice': invoice,
        'lines': invoice.lines.all(),
        'payments': invoice.payments.all(),
    }
    return render(request, 'sales/invoice_detail.html', context)


@login_required
def print_receipt(request, invoice_id):
    """Print/preview receipt"""
    invoice = get_object_or_404(SalesInvoice, id=invoice_id)
    
    context = {
        'invoice': invoice,
        'lines': invoice.lines.all(),
        'payments': invoice.payments.all(),
    }
    return render(request, 'sales/receipt.html', context)


def generate_invoice_number():
    """Generate unique invoice number"""
    from datetime import datetime
    last_invoice = SalesInvoice.objects.order_by('-id').first()
    
    date_prefix = datetime.now().strftime('%Y%m%d')
    sequence = (last_invoice.id + 1) if last_invoice else 1
    
    return f"INV-{date_prefix}-{sequence:05d}"
