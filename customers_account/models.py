from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.conf import settings
import pyotp
import qrcode
from io import BytesIO
import base64
import json
import secrets


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
    id_number = models.CharField(max_length=10, unique=True, null=True, blank=True, verbose_name="身分證字號")
    birth_date = models.DateField(null=True, blank=True, verbose_name="生日")
    phone = models.CharField(max_length=15, null=True, blank=True, verbose_name="電話")

    # 系統自動處理的欄位（綠色標示）
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="註冊時間")
    account_status = models.CharField(
        max_length=20,
        choices=ACCOUNT_STATUS_CHOICES,
        default="active",
        verbose_name="帳號狀態",
    )
    
    # TOTP 二階段驗證相關欄位
    totp_secret_key = models.CharField(
        max_length=32, 
        blank=True, 
        null=True, 
        verbose_name="TOTP 密鑰"
    )
    totp_enabled = models.BooleanField(
        default=False, 
        verbose_name="啟用二階段驗證"
    )
    backup_tokens = models.JSONField(
        default=list,
        blank=True,
        verbose_name="備用恢復代碼"
    )
    totp_verified_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="最後驗證時間"
    )

    class Meta:
        verbose_name = "消費者"
        verbose_name_plural = "消費者"

    def __str__(self):
        return f"{self.name} ({self.member.email if self.member else 'No Email'})"
    
    # TOTP 相關方法
    def generate_totp_secret(self):
        """生成新的 TOTP 密鑰"""
        if not self.totp_secret_key:
            self.totp_secret_key = pyotp.random_base32()
            self.save(update_fields=['totp_secret_key'])
        return self.totp_secret_key
    
    def get_totp_provisioning_uri(self):
        """獲取 TOTP 設定 URI，用於生成 QR Code"""
        if not self.totp_secret_key:
            self.generate_totp_secret()
        
        return pyotp.totp.TOTP(self.totp_secret_key).provisioning_uri(
            name=self.member.email if self.member else self.name,
            issuer_name='TruePay'
        )
    
    def generate_qr_code(self):
        """生成 QR Code 圖片的 base64 編碼"""
        uri = self.get_totp_provisioning_uri()
        
        # 生成 QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        # 創建圖片
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 轉換為 base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_totp(self, token):
        """驗證 TOTP 代碼或備用恢復代碼"""
        from django.contrib.auth.hashers import check_password
        
        if not self.totp_secret_key or not self.totp_enabled:
            return False
        
        # 檢查是否為備用恢復代碼
        for hashed_token in self.backup_tokens:
            if check_password(token, hashed_token):
                # 移除已使用的備用代碼
                self.backup_tokens.remove(hashed_token)
                self.totp_verified_at = timezone.now()
                self.save(update_fields=['backup_tokens', 'totp_verified_at'])
                return True
        
        # 驗證 TOTP 代碼
        totp = pyotp.TOTP(self.totp_secret_key)
        if totp.verify(token, valid_window=1):  # 允許前後30秒的時間窗口
            self.totp_verified_at = timezone.now()
            self.save(update_fields=['totp_verified_at'])
            return True
        
        return False
    
    def generate_backup_tokens(self, count=8):
        """生成備用恢復代碼並安全儲存其雜湊值"""
        from django.contrib.auth.hashers import make_password
        
        plaintext_tokens = []
        hashed_tokens = []
        for _ in range(count):
            token = ''.join(secrets.choice('0123456789') for _ in range(8))
            plaintext_tokens.append(token)
            hashed_tokens.append(make_password(token))
        
        self.backup_tokens = hashed_tokens
        self.save(update_fields=['backup_tokens'])
        return plaintext_tokens
    
    def enable_totp(self):
        """啟用 TOTP 功能"""
        if not self.totp_secret_key:
            self.generate_totp_secret()
        
        self.totp_enabled = True
        
        # 生成備用恢復代碼
        if not self.backup_tokens:
            self.generate_backup_tokens()
        
        self.save(update_fields=['totp_enabled'])
    
    def disable_totp(self):
        """停用 TOTP 功能"""
        self.totp_enabled = False
        self.totp_secret_key = None
        self.backup_tokens = []
        self.totp_verified_at = None
        self.save(update_fields=['totp_enabled', 'totp_secret_key', 'backup_tokens', 'totp_verified_at'])
    
    def is_totp_recently_verified(self, minutes=30):
        """檢查是否在最近指定時間內已驗證過 TOTP"""
        if not self.totp_verified_at:
            return False
        
        time_diff = timezone.now() - self.totp_verified_at
        return time_diff.total_seconds() < (minutes * 60)
