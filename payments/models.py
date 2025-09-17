from django.db import models
from django.utils import timezone
from django.conf import settings
import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import qrcode
from io import BytesIO
import base64
import json
import hmac
import hashlib
import time


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
            
        if self.status not in ["unused", "expired"]:
            return False
            
        if not self.order.is_paid():
            return False
            
        if not self.customer or not self.customer.member or not self.customer.member.email:
            return False
            
        # 檢查是否已經發送過通知
        if self.expiry_notification_sent:
            return False
            
        # 檢查是否在通知時間範圍內
        now = timezone.now()
        notification_time = self.valid_until - timezone.timedelta(minutes=minutes_before)
        
        # 定義通知時間窗口：到期前6分鐘到過期後30分鐘
        window_start = notification_time - timezone.timedelta(minutes=1)  # 到期前6分鐘開始
        window_end = self.valid_until + timezone.timedelta(minutes=30)    # 過期後30分鐘內
        
        # 只在合理的時間窗口內發送通知
        if window_start <= now <= window_end:
            return True
            
        return False
    
    def send_expiry_notification(self):
        """
        發送到期通知郵件
        
        Returns:
            bool: 發送是否成功
        """
        from django.core.mail import send_mail
        from django.conf import settings
        from django.urls import reverse
        
        if not self.should_send_expiry_notification():
            return False
            
        try:
            customer_email = self.customer.member.email
            customer_name = self.customer.name or "親愛的用戶"
            
            # 根據票券是否已過期調整標題和內容
            now = timezone.now()
            if now > self.valid_until:
                subject = "⏰ TruePay 通知 - 您的票券已過期"
                timing_message = "您的票券已過期"
                urgency_level = "提醒"
            else:
                subject = "🚨 TruePay 緊急提醒 - 您的票券即將到期！"
                timing_message = "您的票券即將到期"
                urgency_level = "緊急提醒"
            
            # 生成消費者登入和票券錢包連結
            base_url = f"https://{settings.NGROK_URL}" if hasattr(settings, 'NGROK_URL') else "https://truepay.tw"
            login_url = f"{base_url}/customers/login/"
            wallet_url = f"{base_url}/customers/ticket-wallet/"

            # 純文字版本
            text_message = f"""{customer_name}，您好！

{urgency_level}：{timing_message}！

=== 票券資訊 ===
🏪 商家名稱：{self.product.merchant.ShopName}
🛍️ 商品名稱：{self.product.name}
💰 票券價值：NT$ {self.order.unit_price}
⏰ 到期時間：{timezone.localtime(self.valid_until).strftime("%Y年%m月%d日 %H:%M")}

=== 查看票券詳情 ===
請登入您的 TruePay 帳戶查看完整票券資訊：
📱 票券錢包：{wallet_url}

如果您尚未登入，請先登入：
🔐 登入連結：{login_url}

=== 商家聯絡資訊 ===
🏪 {self.product.merchant.ShopName}
📞 如需協助請直接聯繫商家

=== 重要提醒 ===
• 請在票券錢包中查看完整的票券資訊和 QR Code
• 前往商家時請出示票券 QR Code 進行核銷
• 如有疑問請直接聯繫商家或 TruePay 客服

感謝您使用 TruePay！
TruePay 客服團隊
            """

            # HTML 版本
            html_message = f"""
<div style='font-family: Arial, sans-serif; font-size: 16px; color: #222;'>
<p>{customer_name}，您好！</p>
<p><b>{urgency_level}：</b>{timing_message}！</p>
<hr style='margin: 18px 0;'>
<b>📋 票券資訊</b><br>
🏪 商家名稱：{self.product.merchant.ShopName}<br>
🛍️ 商品名稱：{self.product.name}<br>
💰 票券價值：NT$ {self.order.unit_price}<br>
⏰ 到期時間：{timezone.localtime(self.valid_until).strftime("%Y年%m月%d日 %H:%M")}<br>
<hr style='margin: 18px 0;'>
<b>🔗 查看票券詳情</b><br>
請登入您的 TruePay 帳戶查看完整票券資訊：<br>
📱 票券錢包：<a href='{wallet_url}' style='color: #0056B3;' target='_blank'>{wallet_url}</a><br>
如果您尚未登入，請先登入：<br>
🔐 登入連結：<a href='{login_url}' style='color: #0056B3;' target='_blank'>{login_url}</a><br>
<hr style='margin: 18px 0;'>
<b>📞 商家聯絡資訊</b><br>
🏪 {self.product.merchant.ShopName}<br>
📞 如需協助請直接聯繫商家<br>
<hr style='margin: 18px 0;'>
⚠️ <b>重要提醒：</b><br>
• 請在票券錢包中查看完整的票券資訊和 QR Code<br>
• 前往商家時請出示票券 QR Code 進行核銷<br>
• 如有疑問請直接聯繫商家或 TruePay 客服<br>
<br>
感謝您使用 TruePay！<br>
TruePay 客服團隊
</div>
            """
            send_mail(
                subject=subject,
                message=text_message,  # 純文字版本
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer_email],
                fail_silently=False,
                html_message=html_message,  # HTML 版本
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
        發送所有即將到期或已過期但尚未通知的票券通知
        Returns:
            dict: 執行結果統計
        """
        tickets_to_notify = cls.objects.filter(
            status__in=['unused', 'expired'],
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
        now = timezone.now()
        for ticket in tickets_to_notify:
            total_checked += 1
            # 讓 send_expiry_notification 內部統一處理時間窗口判斷
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
    
    def generate_qr_code_data(self):
        """生成QR code資料內容（含HMAC簽名防偽）"""
        # 生成時間戳
        timestamp = int(time.time())

        # 基本資料
        qr_data = {
            "ticket_code": self.ticket_code,
            "type": "ticket_voucher",
            "version": "1.0",
            "product_id": self.product.id,
            "merchant_id": self.product.merchant.id,
            "timestamp": timestamp
        }

        # 生成HMAC簽名
        signature = self._generate_hmac_signature(qr_data)
        qr_data["signature"] = signature

        return json.dumps(qr_data)
    
    def generate_qr_code_image(self):
        """生成QR code圖片的base64編碼"""
        # 獲取QR code資料
        qr_data = self.generate_qr_code_data()
        
        # 創建QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # 生成圖片
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 轉換為base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def _generate_hmac_signature(self, data):
        """生成HMAC簽名"""
        # 建立簽名字串（排除signature本身）
        sign_data = f"{data['ticket_code']}:{data['product_id']}:{data['merchant_id']}:{data['timestamp']}"

        # 計算HMAC-SHA256簽名
        signature = hmac.new(
            settings.TICKET_HMAC_KEY.encode(),
            sign_data.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    @classmethod
    def verify_qr_signature(cls, qr_data_dict):
        """驗證QR code簽名"""
        # 檢查是否有簽名（向下相容舊版本）
        if "signature" not in qr_data_dict or "timestamp" not in qr_data_dict:
            return True, "舊版本票券，跳過簽名驗證"

        # 提取簽名
        provided_signature = qr_data_dict.get("signature")
        if not provided_signature:
            return False, "缺少簽名資訊"

        # 重新計算預期簽名
        sign_data = f"{qr_data_dict['ticket_code']}:{qr_data_dict['product_id']}:{qr_data_dict['merchant_id']}:{qr_data_dict['timestamp']}"

        expected_signature = hmac.new(
            settings.TICKET_HMAC_KEY.encode(),
            sign_data.encode(),
            hashlib.sha256
        ).hexdigest()

        # 比對簽名
        if not hmac.compare_digest(provided_signature, expected_signature):
            return False, "票券簽名驗證失敗，可能被偽造"

        # 檢查時間戳（防止過舊的票券）
        current_time = int(time.time())
        ticket_time = qr_data_dict.get("timestamp", 0)

        # 允許10分鐘內的時間差（600秒）
        if current_time - ticket_time > 600:
            return False, "票券驗證時間過期"

        return True, "簽名驗證通過"

    @classmethod
    def get_ticket_from_qr_data(cls, qr_data):
        """從QR code資料中取得票券（含簽名驗證）"""
        try:
            data = json.loads(qr_data)
            if data.get("type") != "ticket_voucher":
                return None, "無效的QR code類型"

            # 驗證HMAC簽名
            is_valid, error_message = cls.verify_qr_signature(data)
            if not is_valid:
                return None, error_message

            ticket_code = data.get("ticket_code")
            if not ticket_code:
                return None, "QR code中缺少票券代碼"

            try:
                ticket = cls.objects.get(ticket_code=ticket_code)
                return ticket, None
            except cls.DoesNotExist:
                return None, "找不到對應的票券"

        except json.JSONDecodeError:
            return None, "QR code格式錯誤"


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
