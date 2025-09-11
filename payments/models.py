from django.db import models
from django.utils import timezone
from django.conf import settings
import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction


def default_provider_raw_data():
    """避免可變物件陷阱的預設值函數"""
    return {}


class Order(models.Model):
    """統一訂單模型 - 支援所有金流提供商"""

    PROVIDER_CHOICES = [
        ("newebpay", "藍新金流"),
        ("linepay", "LINE Pay"),
    ]

    STATUS_CHOICES = [
        ("pending", "待付款"),
        ("processing", "處理中"),
        ("paid", "已付款"),
        ("failed", "付款失敗"),
        ("cancelled", "已取消"),
        ("refunded", "已退款"),
    ]

    # === 基本資訊 ===
    # 使用預設 auto-increment ID
    provider = models.CharField("金流提供商", max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField(
        "訂單狀態", max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    amount = models.PositiveIntegerField("訂單金額")
    item_description = models.CharField("商品描述", max_length=200)

    # === 訂單項目資訊 (從 OrderItem 移過來) ===
    quantity = models.PositiveIntegerField("數量", default=1)
    unit_price = models.DecimalField("購買時單價", max_digits=10, decimal_places=2)

    # === 關聯 ===
    product = models.ForeignKey(
        "merchant_marketplace.Product", on_delete=models.CASCADE, verbose_name="商品"
    )
    customer = models.ForeignKey(
        "customers_account.Customer", on_delete=models.CASCADE, verbose_name="客戶"
    )

    # === 時間記錄 ===
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)
    paid_at = models.DateTimeField("付款完成時間", null=True, blank=True)

    # === 通用金流欄位 ===
    provider_order_id = models.CharField("金流訂單ID", max_length=100, unique=True)
    provider_transaction_id = models.CharField("金流交易ID", max_length=100, blank=True)

    # === 藍新金流專用欄位 ===
    newebpay_trade_no = models.CharField("藍新交易序號", max_length=20, blank=True)
    newebpay_payment_type = models.CharField("藍新付款方式", max_length=20, blank=True)
    newebpay_card_info = models.CharField(
        "信用卡資訊", max_length=20, blank=True
    )  # 格式：1234******5678

    # === LINE Pay 專用欄位 ===
    linepay_payment_url = models.URLField("LINE Pay 付款網址", blank=True)

    # === JSON 儲存完整原始資料 ===
    provider_raw_data = models.JSONField(
        "金流原始回傳資料", default=default_provider_raw_data
    )

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]
        verbose_name = "訂單"
        verbose_name_plural = "訂單"

    def __str__(self):
        return (
            f"{self.provider_order_id} - {self.get_status_display()} - NT${self.amount}"
        )

    def save(self, *args, **kwargs):
        """自動生成 provider_order_id 和設定 amount"""
        if not self.provider_order_id:
            if self.provider == "newebpay":
                # 藍新格式：ORD + 時間戳 + 隨機數
                timestamp = timezone.now().strftime("%m%d%H%M%S")
                random_suffix = str(random.randint(1000, 9999))
                self.provider_order_id = f"ORD{timestamp}{random_suffix}"
            elif self.provider == "linepay":
                # LINE Pay 格式：LP + 時間戳 + 隨機數
                timestamp = timezone.now().strftime("%m%d%H%M%S")
                random_suffix = str(random.randint(1000, 9999))
                self.provider_order_id = f"LP{timestamp}{random_suffix}"

        # 確保 amount 與 unit_price * quantity 一致
        if self.unit_price:
            self.amount = int(self.unit_price * self.quantity)

        super().save(*args, **kwargs)

    def is_paid(self):
        """檢查是否已付款成功"""
        return self.status == "paid"

    def get_payment_method_display(self):
        """取得付款方式顯示名稱"""
        return dict(self.PROVIDER_CHOICES).get(self.provider, self.provider)

    def get_card_display(self):
        """取得信用卡號顯示 (藍新金流專用)"""
        if self.provider == "newebpay" and self.newebpay_card_info:
            return self.newebpay_card_info
        return None

    def get_transaction_id_display(self):
        """取得交易編號顯示"""
        if self.provider == "newebpay":
            return self.newebpay_trade_no or self.provider_order_id
        elif self.provider == "linepay":
            return self.provider_transaction_id or self.provider_order_id
        return self.provider_order_id

    @property
    def total_amount(self):
        """訂單總金額"""
        return self.unit_price * self.quantity

    @property
    def merchant_name(self):
        """商家名稱"""
        return self.product.merchant.ShopName

    @property
    def purchase_time(self):
        """購買時間"""
        return self.created_at

    @property
    def customer_name(self):
        """客戶名稱 (透過關聯取得)"""
        return self.customer.name

    @property
    def customer_email(self):
        """客戶Email (透過關聯取得)"""
        return self.customer.member.email

    @property
    def customer_phone(self):
        """客戶電話 (透過關聯取得)"""
        return getattr(self.customer, "phone", "")


class OrderItem(models.Model):
    """票券模型 - 訂單付款成功後產生的獨立票券"""

    STATUS_CHOICES = [
        ("unused", "未使用"),
        ("used", "已使用"),
        ("expired", "已過期"),
    ]

    # === 基本資訊 ===
    ticket_code = models.CharField("票券代碼", max_length=50, unique=True)
    status = models.CharField(
        "票券狀態", max_length=20, choices=STATUS_CHOICES, default="unused"
    )
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    used_at = models.DateTimeField("使用時間", null=True, blank=True)

    # === 票券有效性 ===
    valid_until = models.DateTimeField("有效期限", null=True, blank=True)
    expiry_notification_sent = models.DateTimeField("到期通知發送時間", null=True, blank=True)

    # === 外鍵關聯 ===
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="關聯訂單"
    )
    product = models.ForeignKey(
        "merchant_marketplace.Product", on_delete=models.PROTECT, verbose_name="商品"
    )
    customer = models.ForeignKey(
        "customers_account.Customer",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="客戶",
    )

    class Meta:
        db_table = "order_items"
        ordering = ["-created_at"]
        verbose_name = "票券"
        verbose_name_plural = "票券"

    def __str__(self):
        return f"{self.ticket_code} - {self.get_status_display()}"

    def is_valid(self):
        """檢查票券是否有效（已付款、未使用、未過期）"""
        # 檢查訂單是否已付款
        if not self.order.is_paid():
            return False, "票券尚未付款"

        # 檢查票券是否已使用
        if self.status == "used":
            return False, "票券已使用"

        # 檢查是否過期
        if self.valid_until and timezone.now() > self.valid_until:
            return False, "票券已過期"

        return True, "票券有效"

    def use_ticket(self, merchant):
        """使用票券（需驗證商家權限）"""
        # 檢查是否為該商家的票券
        if self.product.merchant != merchant:
            return False, "您無權限驗證此票券"

        # 檢查票券是否有效
        is_valid, message = self.is_valid()
        if not is_valid:
            return False, message

        # 使用票券
        self.status = "used"
        self.used_at = timezone.now()
        self.save(update_fields=["status", "used_at"])

        return True, "票券使用成功"

    def should_send_expiry_notification(self, minutes_before=5):
        """
        檢查是否應該發送到期通知
        
        Args:
            minutes_before (int): 到期前幾分鐘發送通知
            
        Returns:
            bool: 是否應該發送通知
        """
        # 檢查基本條件
        if not self.valid_until:
            return False
            
        if self.status != "unused":
            return False
            
        if not self.order.is_paid():
            return False
            
        if not self.customer or not self.customer.member or not self.customer.member.email:
            return False
            
        # 檢查是否已經發送過通知
        if self.expiry_notification_sent:
            return False
            
        # 檢查是否在通知時間範圍內（到期前 5 分鐘）
        now = timezone.now()
        notification_time = self.valid_until - timezone.timedelta(minutes=minutes_before)
        
        # 允許一定的時間誤差（例如 1 分鐘），避免因執行時間差而錯過
        time_window_start = notification_time - timezone.timedelta(minutes=1)
        time_window_end = notification_time + timezone.timedelta(minutes=1)
        
        return time_window_start <= now <= time_window_end
    
    def send_expiry_notification(self):
        """
        發送到期通知郵件
        
        Returns:
            bool: 發送是否成功
        """
        from django.core.mail import send_mail
        from django.conf import settings
        
        if not self.should_send_expiry_notification():
            return False
            
        try:
            customer_email = self.customer.member.email
            customer_name = self.customer.name or "親愛的用戶"
            
            subject = "🚨 TruePay 緊急提醒 - 您的票券將在 5 分鐘後到期！"
            
            message = f"""
{customer_name}，您好！

🚨 緊急提醒：您的票券將在 5 分鐘後到期！

請立即前往商家使用，避免票券失效：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 票券詳細資訊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎫 票券代碼：{self.ticket_code}
🏪 商家名稱：{self.product.merchant.ShopName}
🛍️ 商品名稱：{self.product.name}
💰 票券價值：NT$ {self.order.unit_price}
⏰ 到期時間：{self.valid_until.strftime("%Y年%m月%d日 %H:%M")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 商家聯絡資訊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏪 {self.product.merchant.ShopName}
📞 {self.product.phone_number}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 重要提醒：
• 此為最後通知，票券過期後將無法使用
• 請立即前往商家出示票券代碼進行核銷
• 如有疑問請直接聯繫商家

感謝您使用 TruePay！
TruePay 團隊
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer_email],
                fail_silently=False,
            )
            
            # 記錄通知發送時間
            self.expiry_notification_sent = timezone.now()
            self.save(update_fields=['expiry_notification_sent'])
            
            return True
            
        except Exception as e:
            # 這裡可以記錄錯誤日誌
            return False

    @classmethod
    def send_all_expiry_notifications(cls):
        """
        發送所有即將到期票券的通知
        
        Returns:
            dict: 執行結果統計
        """
        # 查找所有需要發送通知的票券
        tickets_to_notify = cls.objects.filter(
            status='unused',
            order__status='paid',
            valid_until__isnull=False,
            expiry_notification_sent__isnull=True,
            customer__isnull=False,
            customer__member__email__isnull=False,
        ).select_related(
            'customer', 
            'customer__member', 
            'product', 
            'product__merchant',
            'order'
        )
        
        notifications_sent = 0
        errors_count = 0
        total_checked = 0
        
        for ticket in tickets_to_notify:
            total_checked += 1
            if ticket.should_send_expiry_notification():
                if ticket.send_expiry_notification():
                    notifications_sent += 1
                else:
                    errors_count += 1
        
        result = {
            'total_checked': total_checked,
            'notifications_sent': notifications_sent,
            'errors_count': errors_count,
            'success_rate': (notifications_sent / total_checked * 100) if total_checked > 0 else 0
        }
        
        return result

    @property
    def ticket_info(self):
        """取得票券資訊（用於模板顯示）"""
        return {
            "product_name": self.product.name,
            "ticket_value": self.order.unit_price,
            "customer_name": self.customer.name if self.customer else "未知客戶",
            "valid_until": self.valid_until,
            "is_used": self.status == "used",
            "used_at": self.used_at,
            "verification_timing": self.product.verification_timing,
            "requires_post_verification": self.product.verification_timing == 'after_redeem',
        }


class TicketValidation(models.Model):
    """票券驗證記錄模型"""

    VALIDATION_STATUS_CHOICES = [
        ("success", "驗證成功"),
        ("failed", "驗證失敗"),
        ("unauthorized", "無權限驗證"),
    ]

    # 關聯欄位
    ticket = models.ForeignKey(OrderItem, on_delete=models.CASCADE, verbose_name="票券")
    merchant = models.ForeignKey(
        "merchant_account.Merchant", on_delete=models.CASCADE, verbose_name="驗證商家"
    )

    # 驗證資訊
    validation_time = models.DateTimeField("驗證時間", auto_now_add=True)
    status = models.CharField(
        "驗證狀態", max_length=20, choices=VALIDATION_STATUS_CHOICES
    )
    failure_reason = models.CharField("失敗原因", max_length=200, blank=True)

    # 驗證方式
    validation_method = models.CharField(
        "驗證方式",
        max_length=20,
        choices=[
            ("qr_code", "QR Code掃描"),
            ("manual", "手動輸入"),
        ],
        default="manual",
    )

    # IP記錄
    ip_address = models.GenericIPAddressField("IP位址", null=True, blank=True)

    class Meta:
        db_table = "ticket_validations"
        ordering = ["-validation_time"]
        verbose_name = "票券驗證記錄"
        verbose_name_plural = "票券驗證記錄"

    def __str__(self):
        return f"{self.ticket.ticket_code} - {self.merchant.ShopName} - {self.get_status_display()}"


# 當訂單付款成功時，透過信號自動生成票券
@receiver(post_save, sender=Order)
def create_tickets(sender, instance, **kwargs):
    """訂單付款成功時自動生成對應數量的票券"""
    # 只處理狀態為「已付款」的訂單
    if instance.status == "paid":
        with transaction.atomic():
            # 使用 select_for_update 鎖定訂單，防止競爭條件
            order = Order.objects.select_for_update().get(pk=instance.pk)

            # 再次檢查是否已生成票券，確保冪等性
            if order.items.exists():
                return

            items_to_create = []
            # 使用更長、更精確的時間戳（包含年份和秒數）
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            order_suffix = str(order.id).zfill(4)[-4:]

            for i in range(order.quantity):
                # 增加隨機數範圍並加上迴圈索引，確保批次內 ticket_code 唯一
                random_suffix = str(random.randint(1000, 9999))
                ticket_code = f"TKT{order_suffix}{timestamp}{i:03d}{random_suffix}"

                # 決定票券有效期限：優先使用商品設定，否則使用全域設定
                if order.product.ticket_expiry:
                    valid_until = order.product.ticket_expiry
                else:
                    valid_until = timezone.now() + timezone.timedelta(days=settings.TICKET_VALIDITY_DAYS)
                
                items_to_create.append(
                    OrderItem(
                        order=order,
                        product=order.product,
                        customer=order.customer,
                        ticket_code=ticket_code,
                        status="unused",
                        valid_until=valid_until,
                    )
                )

            # 使用 bulk_create 進行批量創建以提升性能
            if items_to_create:
                OrderItem.objects.bulk_create(items_to_create)
