from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.conf import settings


class Customer(models.Model):
    member = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="會員帳號",
    )
    ACCOUNT_STATUS_CHOICES = [
        ("active", "啟用"),
        ("inactive", "停用"),
        ("suspended", "暫停"),
    ]

    # 用戶填入的欄位
    name = models.CharField(max_length=100, verbose_name="姓名")
    id_number = models.CharField(max_length=10, unique=True, verbose_name="身分證字號")
    birth_date = models.DateField(verbose_name="生日")
    phone = models.CharField(max_length=15, verbose_name="電話")

    # 系統自動處理的欄位（綠色標示）
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="註冊時間")
    account_status = models.CharField(
        max_length=20,
        choices=ACCOUNT_STATUS_CHOICES,
        default="active",
        verbose_name="帳號狀態",
    )

    class Meta:
        verbose_name = "消費者"
        verbose_name_plural = "消費者"

    def __str__(self):
        return f"{self.name} ({self.member.email if self.member else 'No Email'})"
