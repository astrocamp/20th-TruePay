from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'provider_order_id', 'provider', 'status', 'amount', 
        'customer_name', 'item_description', 'quantity', 'created_at'
    ]
    list_filter = ['provider', 'status', 'created_at']
    search_fields = ['provider_order_id', 'customer__email', 'customer__name', 'item_description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('id', 'provider', 'status', 'amount', 'item_description')
        }),
        ('訂單項目', {
            'fields': ('quantity', 'unit_price')
        }),
        ('客戶資訊', {
            'fields': ('customer',)
        }),
        ('商品資訊', {
            'fields': ('product',)
        }),
        ('金流資訊', {
            'fields': ('provider_order_id', 'provider_transaction_id')
        }),
        ('藍新金流專用', {
            'fields': ('newebpay_trade_no', 'newebpay_payment_type', 'newebpay_card_info'),
            'classes': ('collapse',)
        }),
        ('LINE Pay 專用', {
            'fields': ('linepay_payment_url',),
            'classes': ('collapse',)
        }),
        ('時間記錄', {
            'fields': ('created_at', 'updated_at', 'paid_at')
        }),
        ('原始資料', {
            'fields': ('provider_raw_data',),
            'classes': ('collapse',)
        })
    )
    
    def customer_name(self, obj):
        """透過關聯取得客戶姓名"""
        return obj.customer.name if obj.customer else '-'
    customer_name.short_description = '客戶姓名'