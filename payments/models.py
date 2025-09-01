from django.db import models
from django.utils import timezone
import random
import string


def default_provider_raw_data():
    """避免可變物件陷阱的預設值函數"""
    return {}


class Order(models.Model):
    """統一訂單模型 - 支援所有金流提供商"""
    
    PROVIDER_CHOICES = [
        ('newebpay', '藍新金流'),
        ('linepay', 'LINE Pay'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待付款'),
        ('processing', '處理中'),
        ('paid', '已付款'),
        ('failed', '付款失敗'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
    ]
    
    # === 基本資訊 ===
    # 使用預設 auto-increment ID
    provider = models.CharField('金流提供商', max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField('訂單狀態', max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.PositiveIntegerField('訂單金額')
    item_description = models.CharField('商品描述', max_length=200)
    
    # === 訂單項目資訊 (從 OrderItem 移過來) ===
    quantity = models.PositiveIntegerField('數量', default=1)
    unit_price = models.DecimalField('購買時單價', max_digits=10, decimal_places=2)
    
    # === 關聯 ===
    product = models.ForeignKey('merchant_marketplace.Product', on_delete=models.CASCADE, verbose_name='商品')
    customer = models.ForeignKey('customers_account.Customer', on_delete=models.CASCADE, verbose_name='客戶')
    
    # === 時間記錄 ===
    created_at = models.DateTimeField('建立時間', auto_now_add=True)
    updated_at = models.DateTimeField('更新時間', auto_now=True)
    paid_at = models.DateTimeField('付款完成時間', null=True, blank=True)
    
    # === 通用金流欄位 ===
    provider_order_id = models.CharField('金流訂單ID', max_length=100, unique=True)
    provider_transaction_id = models.CharField('金流交易ID', max_length=100, blank=True)
    
    # === 藍新金流專用欄位 ===
    newebpay_trade_no = models.CharField('藍新交易序號', max_length=20, blank=True)
    newebpay_payment_type = models.CharField('藍新付款方式', max_length=20, blank=True)
    newebpay_card_info = models.CharField('信用卡資訊', max_length=20, blank=True)  # 格式：1234******5678
    
    # === LINE Pay 專用欄位 ===
    linepay_payment_url = models.URLField('LINE Pay 付款網址', blank=True)
    
    # === JSON 儲存完整原始資料 ===
    provider_raw_data = models.JSONField('金流原始回傳資料', default=default_provider_raw_data)
    
    # === 票券相關欄位 ===
    ticket_code = models.CharField('票券驗證碼', max_length=20, blank=True, null=True, unique=True)
    is_ticket_used = models.BooleanField('票券是否已使用', default=False)
    ticket_used_at = models.DateTimeField('票券使用時間', null=True, blank=True)
    ticket_valid_until = models.DateTimeField('票券有效期限', null=True, blank=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        verbose_name = '訂單'
        verbose_name_plural = '訂單'
    
    def __str__(self):
        return f"{self.provider_order_id} - {self.get_status_display()} - NT${self.amount}"
    
    def save(self, *args, **kwargs):
        """自動生成 provider_order_id、設定 amount 和產生票券驗證碼"""
        if not self.provider_order_id:
            if self.provider == 'newebpay':
                # 藍新格式：ORD + 時間戳 + 隨機數
                timestamp = timezone.now().strftime("%m%d%H%M%S")
                random_suffix = str(random.randint(1000, 9999))
                self.provider_order_id = f"ORD{timestamp}{random_suffix}"
            elif self.provider == 'linepay':
                # LINE Pay 格式：LP + 時間戳 + 隨機數
                timestamp = timezone.now().strftime("%m%d%H%M%S")
                random_suffix = str(random.randint(1000, 9999))
                self.provider_order_id = f"LP{timestamp}{random_suffix}"
        
        # 確保 amount 與 unit_price * quantity 一致
        if self.unit_price:
            self.amount = int(self.unit_price * self.quantity)
        
        # 自動生成票券驗證碼（付款成功後）
        if self.status == 'paid' and not self.ticket_code:
            self.ticket_code = self._generate_ticket_code()
            # 設定票券有效期限（預設180天）
            if not self.ticket_valid_until:
                self.ticket_valid_until = timezone.now() + timezone.timedelta(days=180)
        
        super().save(*args, **kwargs)
    
    def is_paid(self):
        """檢查是否已付款成功"""
        return self.status == 'paid'
    
    def get_payment_method_display(self):
        """取得付款方式顯示名稱"""
        return dict(self.PROVIDER_CHOICES).get(self.provider, self.provider)
    
    def get_card_display(self):
        """取得信用卡號顯示 (藍新金流專用)"""
        if self.provider == 'newebpay' and self.newebpay_card_info:
            return self.newebpay_card_info
        return None
    
    def get_transaction_id_display(self):
        """取得交易編號顯示"""
        if self.provider == 'newebpay':
            return self.newebpay_trade_no or self.provider_order_id
        elif self.provider == 'linepay':
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
        return self.customer.email
    
    @property
    def customer_phone(self):
        """客戶電話 (透過關聯取得)"""
        return getattr(self.customer, 'phone', '')
    
    def _generate_ticket_code(self):
        """生成唯一的票券驗證碼"""
        while True:
            # 格式：TC + 8位隨機英數字
            code = 'TC' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Order.objects.filter(ticket_code=code).exists():
                return code
    
    def is_ticket_valid(self):
        """檢查票券是否有效（已付款、未使用、未過期）"""
        if not self.is_paid():
            return False, "票券尚未付款"
        
        if self.is_ticket_used:
            return False, "票券已使用"
        
        if self.ticket_valid_until and timezone.now() > self.ticket_valid_until:
            return False, "票券已過期"
        
        return True, "票券有效"
    
    def use_ticket(self, merchant):
        """使用票券（需驗證商家權限）"""
        # 檢查是否為該商家的票券
        if self.product.merchant != merchant:
            return False, "您無權限驗證此票券"
        
        # 檢查票券是否有效
        is_valid, message = self.is_ticket_valid()
        if not is_valid:
            return False, message
        
        # 使用票券
        self.is_ticket_used = True
        self.ticket_used_at = timezone.now()
        self.save(update_fields=['is_ticket_used', 'ticket_used_at'])
        
        return True, "票券驗證成功"
    
    @property
    def ticket_info(self):
        """取得票券資訊（用於模板顯示）"""
        return {
            'product_name': self.item_description,
            'ticket_value': self.amount,
            'customer_name': self.customer_name,
            'valid_until': self.ticket_valid_until,
            'is_used': self.is_ticket_used,
            'used_at': self.ticket_used_at,
        }


class TicketValidation(models.Model):
    """票券驗證記錄模型"""
    
    VALIDATION_STATUS_CHOICES = [
        ('success', '驗證成功'),
        ('failed', '驗證失敗'),
        ('unauthorized', '無權限驗證'),
    ]
    
    # 關聯欄位
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name='票券訂單')
    merchant = models.ForeignKey('merchant_account.Merchant', on_delete=models.CASCADE, verbose_name='驗證商家')
    
    # 驗證資訊
    validation_time = models.DateTimeField('驗證時間', auto_now_add=True)
    status = models.CharField('驗證狀態', max_length=20, choices=VALIDATION_STATUS_CHOICES)
    failure_reason = models.CharField('失敗原因', max_length=200, blank=True)
    
    # 驗證方式
    validation_method = models.CharField('驗證方式', max_length=20, choices=[
        ('qr_code', 'QR Code掃描'),
        ('manual', '手動輸入'),
    ], default='manual')
    
    # IP記錄
    ip_address = models.GenericIPAddressField('IP位址', null=True, blank=True)
    
    class Meta:
        db_table = 'ticket_validations'
        ordering = ['-validation_time']
        verbose_name = '票券驗證記錄'
        verbose_name_plural = '票券驗證記錄'
    
    def __str__(self):
        return f"{self.order.ticket_code} - {self.merchant.ShopName} - {self.get_status_display()}"