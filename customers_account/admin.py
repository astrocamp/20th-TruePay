from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "account_status", "created_at"]
    list_filter = ["account_status", "created_at"]
    search_fields = ["name", "phone", "id_number"]
    readonly_fields = ["created_at"]

    fieldsets = (
        (
            "基本資料",
            {
                "fields": (
                    "name",
                    "id_number",
                    "birth_date",
                    "phone",
                )
            },
        ),
        (
            "帳號狀態",
            {"fields": ("account_status",)},
        ),
        (
            "系統資訊",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        # 可以根據需求限制刪除權限
        return request.user.is_superuser
