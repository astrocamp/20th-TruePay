import hashlib
from urllib.parse import parse_qs
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.conf import settings
from django.utils import timezone


class NewebPayUtils:
    """藍新金流工具類 - 處理加密、解密、參數生成等核心功能"""

    def __init__(self):
        self.merchant_id = settings.NEWEBPAY_MERCHANT_ID
        self.hash_key = settings.NEWEBPAY_HASH_KEY
        self.hash_iv = settings.NEWEBPAY_HASH_IV

    def generate_aes_encrypt(self, trade_info):
        """
        AES-256-CBC 加密
        藍新金流要求使用 AES-256-CBC 模式加密付款參數
        重要：藍新金流需要十六進制格式，不是 Base64
        """
        # 將 dict 轉為查詢字串格式
        if isinstance(trade_info, dict):
            trade_info = "&".join([f"{k}={v}" for k, v in trade_info.items()])

        # 使用 HashKey 和 HashIV 進行 AES 加密
        cipher = AES.new(
            self.hash_key.encode("utf-8"), AES.MODE_CBC, self.hash_iv.encode("utf-8")
        )

        # PKCS7 填充並加密
        encrypted = cipher.encrypt(pad(trade_info.encode("utf-8"), AES.block_size))

        # 轉換為十六進制字串（藍新金流規範）
        encrypted_hex = encrypted.hex()
        return encrypted_hex

    def generate_sha256_check_value(self, aes_encrypt_data):
        """
        產生 SHA256 檢查碼
        藍新金流規範: HashKey={HashKey}&{TradeInfo}&HashIV={HashIV}
        注意: TradeInfo 直接使用十六進制加密字串，不需要 URL 解碼
        """
        # 直接使用十六進制加密字串
        check_value = (
            f"HashKey={self.hash_key}&{aes_encrypt_data}&HashIV={self.hash_iv}"
        )
        sha256_hash = hashlib.sha256(check_value.encode("utf-8")).hexdigest().upper()
        return sha256_hash

    def aes_decrypt(self, encrypted_data):
        """
        AES 解密 - 用來解密藍新金流回傳的資料
        藍新金流回傳的資料是十六進制格式
        改進版：智能處理不同長度的 TradeInfo (notify: 1024, return: 1088)
        """
        try:
            # 檢查是否為有效十六進制
            if not all(c in "0123456789abcdefABCDEF" for c in encrypted_data):
                print(f"錯誤：不是有效的十六進制字串")
                return None

            # 十六進制字串轉換為 bytes 並解密
            encrypted_bytes = bytes.fromhex(encrypted_data)
            cipher = AES.new(
                self.hash_key.encode("utf-8"),
                AES.MODE_CBC,
                self.hash_iv.encode("utf-8"),
            )
            decrypted = cipher.decrypt(encrypted_bytes)
            
            # 智能解密策略：嘗試不同解密方法
            decrypted_data = None
            
            # 方法1：標準 PKCS7 解密
            try:
                decrypted_data = unpad(decrypted, AES.block_size).decode("utf-8")
                print(f"標準 PKCS7 解密成功")
            except ValueError:
                # 方法2：智能 JSON 邊界檢測（針對藍新金流 return 回調）
                try:
                    full_text = decrypted.decode("utf-8", errors="ignore")
                    last_brace = full_text.rfind("}")
                    if last_brace != -1:
                        json_candidate = full_text[:last_brace + 1]
                        # 驗證是否為有效 JSON
                        import json
                        json.loads(json_candidate)
                        decrypted_data = json_candidate
                        print(f"JSON 邊界解密成功")
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    pass
                
                # 方法3：嘗試常見長度截斷
                if not decrypted_data:
                    for target_length in [512, 496, 480, 464, 448]:
                        if len(decrypted) >= target_length:
                            try:
                                truncated = decrypted[:target_length]
                                decrypted_data = unpad(truncated, AES.block_size).decode("utf-8")
                                print(f"截斷解密成功 ({target_length} bytes)")
                                break
                            except (ValueError, UnicodeDecodeError):
                                continue
            
            if not decrypted_data:
                print("解密失敗：所有方法都無效")
                return None

            # 解析為 JSON 或 query string
            import json
            try:
                json_data = json.loads(decrypted_data)
                return json_data
            except json.JSONDecodeError:
                # 如果不是 JSON，嘗試解析為 query string
                return dict(parse_qs(decrypted_data, keep_blank_values=True))

        except Exception as e:
            print(f"解密錯誤: {e}")
            return None

    def generate_trade_info(self, payment_data):
        """
        產生交易資訊參數
        按照藍新金流官方文件的參數順序
        """
        from collections import OrderedDict

        # 使用固定時間戳格式，避免時間相關問題
        import time

        timestamp = str(int(time.time()))

        # 使用 OrderedDict 確保參數順序
        trade_info = OrderedDict(
            [
                ("MerchantID", self.merchant_id),
                ("RespondType", "JSON"),
                ("TimeStamp", timestamp),
                ("Version", "2.3"),  # 使用正確的 API 版本
                ("MerchantOrderNo", payment_data["merchant_order_no"]),
                ("Amt", str(payment_data["amt"])),
                ("ItemDesc", payment_data["item_desc"]),
                ("ReturnURL", settings.PAYMENT_RETURN_URL),
                ("NotifyURL", settings.PAYMENT_NOTIFY_URL),
                ("ClientBackURL", settings.PAYMENT_CANCEL_URL),
                ("Email", payment_data.get("email", "")),
                ("CREDIT", "1"),
            ]
        )
        return trade_info

    def create_payment_form_data(self, payment_data):
        """
        建立完整的付款表單資料
        返回可以直接送給藍新金流的參數
        """
        # 1. 產生交易資訊
        trade_info = self.generate_trade_info(payment_data)

        # 2. 將交易資訊加密
        trade_info_aes = self.generate_aes_encrypt(trade_info)

        # 3. 產生檢查碼
        trade_sha = self.generate_sha256_check_value(trade_info_aes)

        # 4. 組合最終的表單資料
        form_data = {
            "MerchantID": self.merchant_id,
            "TradeInfo": trade_info_aes,
            "TradeSha": trade_sha,
            "Version": "2.3",  # 與 TradeInfo 內的版本保持一致
        }

        return form_data

    def verify_notify_data(self, received_data):
        """
        驗證藍新金流回傳的通知資料
        確保資料沒有被竄改
        """
        try:
            # 1. 重新計算檢查碼
            calculated_sha = self.generate_sha256_check_value(
                received_data["TradeInfo"]
            )

            # 2. 比對檢查碼
            if calculated_sha != received_data["TradeSha"]:
                return False, "檢查碼不符"

            # 3. 解密交易資訊
            decrypted_data = self.aes_decrypt(received_data["TradeInfo"])
            if not decrypted_data:
                return False, "解密失敗"

            return True, decrypted_data

        except Exception as e:
            return False, f"驗證失敗: {e}"
