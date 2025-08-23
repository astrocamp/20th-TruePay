from django.db import models
from django.utils import timezone
import uuid


class Payment(models.Model):
    """藍新金流付款記錄模型"""

    PAYMENT_STATUS_CHOICES = [
        ("pending", "待付款"),
        ("paid", "已付款"),
        ("failed", "付款失敗"),
        ("refunded", "已退款"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant_order_no = models.CharField(
        max_length=30, unique=True, verbose_name="商店訂單編號"
    )
    amt = models.PositiveBigIntegerField("付款金額")
    item_desc = models.CharField(max_length=100, verbose_name="商品描述")
    status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
        verbose_name="付款狀態",
    )

    # 客戶資訊
    email = models.EmailField("客戶 Email", blank=True)
    customer_name = models.CharField("客戶姓名", max_length=20, blank=True)
    customer_phone = models.CharField("客戶電話", max_length=20, blank=True)

    # 藍新金流回傳資訊
    trade_no = models.CharField(
        "藍新金流交易序號", max_length=20, blank=True, null=True
    )
    payment_type = models.CharField("付款方式", max_length=20, blank=True, null=True)
    pay_time = models.DateTimeField("付款完成時間", blank=True, null=True)

    # 信用卡相關資訊（信用卡付款時會用到）
    auth_bank = models.CharField("收單銀行", max_length=10, blank=True, null=True)
    respond_code = models.CharField("銀行回應碼", max_length=5, blank=True, null=True)
    auth = models.CharField("授權碼", max_length=6, blank=True, null=True)
    card_6no = models.CharField("信用卡前六碼", max_length=6, blank=True, null=True)
    card_4no = models.CharField("信用卡後四碼", max_length=4, blank=True, null=True)

    # 系統記錄
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)

    # 回調記錄
    return_received = models.BooleanField("已收到返回通知", default=False)
    notify_received = models.BooleanField("已收到後台通知", default=False)
    notify_data = models.JSONField("後台通知原始資料", blank=True, null=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]
        verbose_name = "付款記錄"
        verbose_name_plural = "付款記錄"

    def __str__(self):
        return f"{self.merchant_order_no} - {self.get_status_display()} - NT${self.amt}"

    def is_paid(self):
        """檢查是否已付款成功"""
        return self.status == "paid"

    def save(self, *args, **kwargs):
        # 如果沒有訂單編號，生成一個（檢查是否為新記錄用 _state.adding）
        if not self.merchant_order_no:
            import random

            # 使用短的時間戳記 + 隨機數，確保在30字符內
            timestamp = timezone.now().strftime("%m%d%H%M%S")  # 10個字符
            random_suffix = str(random.randint(1000, 9999))  # 4個字符
            self.merchant_order_no = f"ORD{timestamp}{random_suffix}"  # 總共17字符

        super().save(*args, **kwargs)
