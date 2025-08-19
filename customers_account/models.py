from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone


class Customer(models.Model):
    ACCOUNT_STATUS_CHOICES = [
        ('active', '啟用'),
        ('inactive', '停用'),
        ('suspended', '暫停'),
    ]
    
    # 用戶填入的欄位
    email = models.EmailField(unique=True, verbose_name="電子郵件")
    password = models.CharField(max_length=128, verbose_name="密碼")
    name = models.CharField(max_length=100, verbose_name="姓名")
    id_number = models.CharField(max_length=10, unique=True, verbose_name="身分證字號")
    birth_date = models.DateField(verbose_name="生日")
    phone = models.CharField(max_length=15, verbose_name="電話")
    
    # 系統自動處理的欄位（綠色標示）
    email_verified = models.BooleanField(default=False, verbose_name="Email驗證狀態")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="註冊時間")
    last_login = models.DateTimeField(null=True, blank=True, verbose_name="最後登入時間")
    login_failed_count = models.IntegerField(default=0, verbose_name="登入失敗次數")
    account_status = models.CharField(
        max_length=20, 
        choices=ACCOUNT_STATUS_CHOICES, 
        default='active', 
        verbose_name="帳號狀態"
    )
    reset_password_token = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="重設密碼Token"
    )
    
    class Meta:
        verbose_name = "消費者"
        verbose_name_plural = "消費者"
        
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def set_password(self, raw_password):
        """設定密碼（自動加密）"""
        self.password = make_password(raw_password)
        
    def check_password(self, raw_password):
        """檢查密碼"""
        return check_password(raw_password, self.password)
    
    def update_last_login(self):
        """更新最後登入時間"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])
        
    def increment_login_failed_count(self):
        """增加登入失敗次數"""
        self.login_failed_count += 1
        self.save(update_fields=['login_failed_count'])
        
    def reset_login_failed_count(self):
        """重設登入失敗次數"""
        self.login_failed_count = 0
        self.save(update_fields=['login_failed_count'])
