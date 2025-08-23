from django.db import models
from django.db import models
from merchant_marketplace.models import Product

class Order(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # 關聯商品
    total_price = models.IntegerField()  # 訂單金額（整數即可，TWD）
    status = models.CharField(max_length=20, default="pending")  # 訂單狀態：pending, paid, cancelled
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"


