#!/usr/bin/env python3
"""
手動測試藍新金流回調資料解密
使用方式: python test_newebpay_callback.py "你的TradeInfo資料"
"""
import os
import sys
import django

# 設定 Django 環境
sys.path.append('/Users/magic/20th-TruePay')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'truepay.settings')
django.setup()

from django.conf import settings
from payments.views import aes_decrypt
import json

def test_callback_data(trade_info_data):
    """測試回調資料解密"""
    print(f"=== 測試藍新金流回調資料解密 ===")
    print(f"輸入資料長度: {len(trade_info_data)}")
    print(f"資料開頭: {trade_info_data[:100]}...")
    
    hash_key = settings.NEWEBPAY_HASH_KEY
    hash_iv = settings.NEWEBPAY_HASH_IV
    
    try:
        decrypted = aes_decrypt(trade_info_data, hash_key, hash_iv)
        print(f"\n✅ 解密成功!")
        print(f"解密後資料: {decrypted}")
        
        # 嘗試解析 JSON
        try:
            json_data = json.loads(decrypted)
            print(f"\n✅ JSON 解析成功!")
            print(f"解析結果: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON 解析失敗: {e}")
            
    except Exception as e:
        print(f"\n❌ 解密失敗: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方式: python test_newebpay_callback.py '你的TradeInfo資料'")
        print("範例: python test_newebpay_callback.py 'ff2c4f...'")
        sys.exit(1)
    
    trade_info = sys.argv[1]
    test_callback_data(trade_info)