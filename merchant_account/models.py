from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from cryptography.fernet import Fernet
import os
import base64
import logging

logger = logging.getLogger(__name__)


# Create your models here.
class Merchant(models.Model):
    ShopName = models.CharField(max_length=50, null=False)
    UnifiedNumber = models.CharField(max_length=8, null=False)
    NationalNumber = models.CharField(max_length=10, null=False)
    Email = models.EmailField(unique=True, null=False)
    Name = models.CharField(max_length=30, null=False)
    Address = models.CharField(max_length=50, null=False)
    Cellphone = models.CharField(max_length=15, null=False)
    Password = models.CharField(max_length=128, null=False)
    subdomain = models.SlugField(max_length=50, unique=True, null=True, blank=True)
    merchant_domain = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="自訂域名"
    )
    use_merchant_domain = models.BooleanField(
        default=False, verbose_name="使用自訂域名"
    )
    
    # 金流設定欄位
    newebpay_merchant_id = models.CharField(max_length=50, blank=True, verbose_name="藍新金流商店代號")
    newebpay_hash_key = models.TextField(blank=True, verbose_name="藍新金流HashKey(加密)")
    newebpay_hash_iv = models.TextField(blank=True, verbose_name="藍新金流HashIV(加密)")
    linepay_channel_id = models.CharField(max_length=50, blank=True, verbose_name="LINE Pay Channel ID")
    linepay_channel_secret = models.TextField(blank=True, verbose_name="LINE Pay Channel Secret(加密)")
    
    # 金流設定狀態
    payment_setup_completed = models.BooleanField(default=False, verbose_name="金流設定完成")

    def __str__(self):
        return self.ShopName

    def set_password(self, raw_password):
        self.Password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.Password)
    
    @staticmethod
    def _get_encryption_key():
        """取得加密金鑰"""
        key = os.getenv('PAYMENT_ENCRYPTION_KEY', 'dev-key-32chars-for-testing-only!')
        if isinstance(key, str):
            key = key.encode()
        # 確保金鑰長度正確
        return base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))
    
    def _encrypt_data(self, data):
        """加密敏感資料"""
        if not data:
            return ''
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            return base64.urlsafe_b64encode(fernet.encrypt(data.encode())).decode()
        except Exception as e:
            logger.error(f"資料加密失敗: {e}")
            return data
    
    def _decrypt_data(self, encrypted_data):
        """解密敏感資料"""
        if not encrypted_data:
            return ''
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            return fernet.decrypt(decoded_data).decode()
        except Exception as e:
            logger.error(f"資料解密失敗: {e}")
            return encrypted_data
    
    def set_payment_keys(self, **kwargs):
        """設定金流金鑰（自動加密敏感資料）"""
        if 'newebpay_merchant_id' in kwargs:
            self.newebpay_merchant_id = kwargs['newebpay_merchant_id']
        if 'newebpay_hash_key' in kwargs:
            self.newebpay_hash_key = self._encrypt_data(kwargs['newebpay_hash_key'])
        if 'newebpay_hash_iv' in kwargs:
            self.newebpay_hash_iv = self._encrypt_data(kwargs['newebpay_hash_iv'])
        if 'linepay_channel_id' in kwargs:
            self.linepay_channel_id = kwargs['linepay_channel_id']
        if 'linepay_channel_secret' in kwargs:
            self.linepay_channel_secret = self._encrypt_data(kwargs['linepay_channel_secret'])
        
        # 更新設定狀態
        self.update_payment_setup_status()
    
    def get_payment_keys(self):
        """取得解密後的金流金鑰"""
        return {
            'newebpay_merchant_id': self.newebpay_merchant_id,
            'newebpay_hash_key': self._decrypt_data(self.newebpay_hash_key),
            'newebpay_hash_iv': self._decrypt_data(self.newebpay_hash_iv),
            'linepay_channel_id': self.linepay_channel_id,
            'linepay_channel_secret': self._decrypt_data(self.linepay_channel_secret),
        }
    
    def get_masked_keys(self):
        """取得部分遮蔽的金鑰用於顯示"""
        def mask_key(key, visible=4):
            if not key or len(key) <= visible:
                return key
            return key[:visible] + '*' * (len(key) - visible)
        
        keys = self.get_payment_keys()
        return {
            'newebpay_merchant_id': keys['newebpay_merchant_id'],
            'newebpay_hash_key': mask_key(keys['newebpay_hash_key']),
            'newebpay_hash_iv': mask_key(keys['newebpay_hash_iv']),
            'linepay_channel_id': keys['linepay_channel_id'],
            'linepay_channel_secret': mask_key(keys['linepay_channel_secret']),
        }
    
    def update_payment_setup_status(self):
        """更新金流設定完成狀態"""
        # 檢查是否至少完成一組金流設定
        has_newebpay = all([self.newebpay_merchant_id, self.newebpay_hash_key, self.newebpay_hash_iv])
        has_linepay = all([self.linepay_channel_id, self.linepay_channel_secret])
        self.payment_setup_completed = has_newebpay or has_linepay
    
    def has_newebpay_setup(self):
        """檢查是否已設定藍新金流"""
        return all([self.newebpay_merchant_id, self.newebpay_hash_key, self.newebpay_hash_iv])
    
    def has_linepay_setup(self):
        """檢查是否已設定LINE Pay"""
        return all([self.linepay_channel_id, self.linepay_channel_secret])
