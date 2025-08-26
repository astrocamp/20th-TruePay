#!/usr/bin/env python3
"""
測試藍新金流 AES 解密設定
"""
import os
import django
import sys

# 設定 Django 環境
sys.path.append('/Users/magic/20th-TruePay')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'truepay.settings')
django.setup()

from django.conf import settings
from payments.views import aes_encrypt, aes_decrypt

def test_newebpay_settings():
    """測試藍新金流設定"""
    print("=== 藍新金流設定檢查 ===")
    
    # 檢查環境變數
    merchant_id = settings.NEWEBPAY_MERCHANT_ID
    hash_key = settings.NEWEBPAY_HASH_KEY  
    hash_iv = settings.NEWEBPAY_HASH_IV
    
    print(f"MERCHANT_ID: {'已設定' if merchant_id else '❌ 未設定'}")
    print(f"HASH_KEY: {'已設定' if hash_key else '❌ 未設定'} (長度: {len(hash_key) if hash_key else 0})")
    print(f"HASH_IV: {'已設定' if hash_iv else '❌ 未設定'} (長度: {len(hash_iv) if hash_iv else 0})")
    
    if not hash_key or not hash_iv:
        print("❌ 重要設定缺失！請檢查 .env 檔案")
        return False
    
    # 檢查長度
    if len(hash_key) != 32:
        print(f"⚠️  HASH_KEY 長度不正確，應為 32 字符，實際 {len(hash_key)}")
    if len(hash_iv) != 16:
        print(f"⚠️  HASH_IV 長度不正確，應為 16 字符，實際 {len(hash_iv)}")
    
    print("\n=== AES 加解密測試 ===")
    
    # 測試加解密
    test_data = "MerchantID=123456&Amt=100&ItemDesc=測試商品"
    print(f"原始資料: {test_data}")
    
    try:
        # 加密
        encrypted = aes_encrypt(test_data, hash_key, hash_iv)
        print(f"加密結果: {encrypted[:50]}...")
        
        # 解密
        decrypted = aes_decrypt(encrypted, hash_key, hash_iv)
        print(f"解密結果: {decrypted}")
        
        if test_data == decrypted:
            print("✅ 加解密測試成功")
            return True
        else:
            print("❌ 加解密測試失敗 - 資料不一致")
            return False
            
    except Exception as e:
        print(f"❌ 加解密測試失敗: {e}")
        return False

if __name__ == "__main__":
    success = test_newebpay_settings()
    if not success:
        print("\n建議檢查項目:")
        print("1. 確認 .env 檔案中的 NEWEBPAY_HASH_KEY 和 NEWEBPAY_HASH_IV")
        print("2. 確認 Key 長度為 32 字符，IV 長度為 16 字符") 
        print("3. 確認沒有多餘的空格或換行符")
        sys.exit(1)
    else:
        print("\n✅ 所有測試通過！")