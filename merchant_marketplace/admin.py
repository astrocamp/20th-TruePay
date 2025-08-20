from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'merchant', 'price', 'phone_number', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'merchant']
    search_fields = ['name', 'merchant__ShopName', 'phone_number']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
