from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'products'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='list'),
    path('add/', views.ProductCreateView.as_view(), name='add'),
    path('inventory/', views.InventoryView.as_view(), name='inventory'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ProductUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ProductDeleteView.as_view(), name='delete'),
    path('<int:product_id>/adjust-stock/', views.StockAdjustmentView.as_view(), name='adjust-stock'),
    path('export/', views.ExportProductsView.as_view(), name='export'),
    path('variants/<int:product_pk>/add/', views.ProductVariantCreateView.as_view(), name='variant-add'),
    path('categories/', views.ProductcategoryListView.as_view(), name='category-list'),
    path('categories/add/', views.create_categoryView.as_view(), name='category-add'),
    path('categories/export/', views.ExportCategoriesView.as_view(), name='category-export'),
    path('suppliers/add/', views.create_supplierView.as_view(), name='supplier-add'),
    path('suppliers/', views.ProductSupplierListView.as_view(), name='supplier-list'),
    path('suppliers/<int:pk>/edit/', views.supplier_update_view, name='supplier-edit'),
    path('suppliers/export/', views.ExportSuppliersView.as_view(), name='supplier-export'),
    path('categories/<int:pk>/delete/', views.category_deleteview.as_view(), name='category-delete'),
    path('suppliers/<int:pk>/delete/', views.supplier_deleteview.as_view(), name='supplier-delete'),
    path('export/', views.ExportProductsView.as_view(), name='export'),
    path('export/categories/', views.ExportCategoriesView.as_view(), name='category-export'),
    path('export/suppliers/', views.ExportSuppliersView.as_view(), name='supplier-export'),
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)