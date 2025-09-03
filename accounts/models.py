from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Member(AbstractUser):
    member_type_choices = [
        ("customer", "消費者"),
        ("merchant", "商家"),
    ]

    member_type = models.CharField(
        max_length=20, choices=member_type_choices, verbose_name="會員類型"
    )
    phone = models.CharField(max_length=15, blank=True, verbose_name="電話")
    login_failed_count = models.IntegerField(default=0, verbose_name="登入失敗次數")
    email_verified = models.BooleanField(default=False, verbose_name="Email驗證狀態")
    reset_password_token = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="重設密碼Token"
    )

    class Meta:
        verbose_name = "會員"
        verbose_name_plural = "會員"

    def __str__(self):
        return f"{self.username}({self.get_member_type_display()})"

    def update_last_login(self):
        self.last_login = timezone.now()
        self.save(update_fields=["last_login"])
