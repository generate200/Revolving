from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'products'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='list'),
    path('add/', views.ProductCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', views.ProductUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ProductDeleteView.as_view(), name='delete'),
    path('categories/', views.ProductcategoryListView.as_view(), name='category-list'),
    path('categories/add/', views.create_categoryView.as_view(), name='category-add'),
    path('suppliers/add/', views.create_supplierView.as_view(), name='supplier-add'),
    path('suppliers/', views.ProductSupplierListView.as_view(), name='supplier-list'),
    path('categories/<int:pk>/delete/', views.category_deleteview.as_view(), name='category-delete'),
    path('suppliers/<int:pk>/delete/', views.supplier_deleteview.as_view(), name='supplier-delete'),
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)