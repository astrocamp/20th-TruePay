from django.db import models
from merchant_account.models import Merchant
from .validators import validate_image_file


class Product(models.Model):
    VERIFICATION_TIMING_CHOICES = [
        ('before_payment', '付款前驗證'),
        ('before_redeem', '核銷前驗證'),
        ('after_redeem', '核銷後驗證'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="商品名稱")
    description = models.TextField(verbose_name="商品介紹")
    price = models.PositiveIntegerField(verbose_name="商品價格")
    stock = models.PositiveIntegerField(default=1, verbose_name="庫存數量")
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        verbose_name="商品圖片",
        help_text="支援 JPG、PNG、GIF、WebP 格式，檔案大小不超過 5MB"
    )
    phone_number = models.CharField(max_length=20, verbose_name="電話號碼")
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, verbose_name="商家")
    verification_timing = models.CharField(
        max_length=20,
        choices=VERIFICATION_TIMING_CHOICES,
        default='before_redeem',
        verbose_name="驗證時間點"
    )
    ticket_expiry = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="票券有效期限",
        help_text="設定此商品票券的有效期限，留空則使用系統預設值"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    is_active = models.BooleanField(default=True, verbose_name="是否上架")

    class Meta:
        verbose_name = "商品"
        verbose_name_plural = "商品"
        ordering = ['-created_at']

    def __str__(self):
        return self.name
