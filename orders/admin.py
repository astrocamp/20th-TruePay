from django.contrib import admin
from .models import OrderItem


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'payment', 'customer', 'product', 'merchant_name', 
        'quantity', 'unit_price', 'total_amount', 'payment_provider', 'purchase_time'
    ]
    list_filter = ['payment_provider', 'payment__status', 'payment__created_at']
    search_fields = ['payment__merchant_order_no', 'product__name', 'customer__name']
    readonly_fields = ['total_amount', 'purchase_time', 'merchant_name']
    
    fieldsets = (
        ('訂單資訊', {
            'fields': ('payment', 'customer', 'product', 'payment_provider')
        }),
        ('商品資訊', {
            'fields': ('quantity', 'unit_price', 'total_amount')
        }),
        ('系統資訊', {
            'fields': ('purchase_time', 'merchant_name'),
            'classes': ('collapse',)
        }),
    )
