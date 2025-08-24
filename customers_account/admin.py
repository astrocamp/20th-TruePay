from django.contrib import admin
from .models import Customer, PurchaseRecord


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'account_status', 'email_verified', 'created_at', 'last_login']
    list_filter = ['account_status', 'email_verified', 'created_at']
    search_fields = ['name', 'email', 'phone', 'id_number']
    readonly_fields = ['created_at', 'last_login', 'login_failed_count', 'reset_password_token']
    
    fieldsets = (
        ('基本資料', {
            'fields': ('email', 'name', 'id_number', 'birth_date', 'phone')
        }),
        ('帳號狀態', {
            'fields': ('account_status', 'email_verified', 'login_failed_count')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'last_login', 'reset_password_token'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # 可以根據需求限制刪除權限
        return request.user.is_superuser


@admin.register(PurchaseRecord)
class PurchaseRecordAdmin(admin.ModelAdmin):
    list_display = ['payment', 'product', 'quantity', 'unit_price', 'total_price', 'purchase_time']
    list_filter = ['payment__status', 'payment__created_at']
    search_fields = ['payment__merchant_order_no', 'product__name']
    readonly_fields = ['purchase_time', 'merchant_name']
