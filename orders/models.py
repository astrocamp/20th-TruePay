from django.db import models


class OrderItem(models.Model):
    """訂單項目"""
    
    PAYMENT_PROVIDER_CHOICES = [
        ('newebpay', '藍新金流'),
        ('linepay', 'LinePay'),
    ]
    
    payment = models.OneToOneField(
        'newebpay.Payment', 
        on_delete=models.CASCADE,
        to_field='merchant_order_no',
        verbose_name="付款記錄"
    )
    customer = models.ForeignKey(
        'customers_account.Customer', 
        on_delete=models.CASCADE, 
        verbose_name="消費者"
    )
    product = models.ForeignKey(
        'merchant_marketplace.Product', 
        on_delete=models.CASCADE, 
        verbose_name="商品"
    )
    quantity = models.PositiveIntegerField(verbose_name="數量")
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="購買時單價"
    )
    payment_provider = models.CharField(
        max_length=20,
        choices=PAYMENT_PROVIDER_CHOICES,
        default='newebpay',
        verbose_name="付款服務提供者"
    )
    
    class Meta:
        verbose_name = "訂單項目"
        verbose_name_plural = "訂單項目"
        ordering = ['-payment__created_at']
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    @property
    def total_amount(self):
        """商品總金額"""
        return self.unit_price * self.quantity
        
    @property
    def merchant_name(self):
        """商家名稱"""
        return self.product.merchant.ShopName
    
    @property
    def purchase_time(self):
        """購買時間"""
        return self.payment.created_at
    
    def get_payment_method_display(self):
        """取得付款方式顯示"""
        if self.payment_provider == 'linepay':
            return 'LinePay'
        elif self.payment_provider == 'newebpay':
            return '藍新金流'
        else:
            return self.get_payment_provider_display()
