from django.db import models
from merchant_account.models import Merchant


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="商品名稱")
    description = models.TextField(verbose_name="商品介紹")
    price = models.PositiveIntegerField(verbose_name="商品價格")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="商品圖片")
    phone_number = models.CharField(max_length=20, verbose_name="電話號碼")
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, verbose_name="商家")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    is_active = models.BooleanField(default=True, verbose_name="是否上架")

    class Meta:
        verbose_name = "商品"
        verbose_name_plural = "商品"
        ordering = ['-created_at']

    def __str__(self):
        return self.name
