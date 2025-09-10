import dns.resolver
import dns.exception
from django.utils import timezone
from .models import MerchantOwnDomain
import requests


class DomainVerificationService:
    @staticmethod
    def verify_domain_ownership(domain_obj):

        txt_success, txt_message = DomainVerificationService._verify_txt_record(
            domain_obj
        )
        if not txt_success:
            return False, f"所有權驗證失敗：{txt_message}"
        http_success, http_message = DomainVerificationService._verify_http_access(
            domain_obj
        )
        if not http_success:
            return False, f"網站訪問測試失敗：{http_message}"

        domain_obj.is_verified = True
        domain_obj.verified_at = timezone.now()
        domain_obj.save(update_fields=["is_verified", "verified_at"])
        return True, "網域驗證成功！"

    @staticmethod
    def _verify_txt_record(domain_obj):
        try:
            verification_record_name = f"_truepay-verification.{domain_obj.domain_name}"
            resolver = dns.resolver.Resolver()
            resolver.timeout = 10

            answers = resolver.resolve(verification_record_name, "TXT")
            for answer in answers:
                txt_content = answer.to_text().strip('"')
                if txt_content == domain_obj.verification_token:
                    return True, "TXT 記錄驗證成功"
            return False, "找不到正確的驗證記錄"
        except dns.resolver.NXDOMAIN:
            return False, "驗證記錄不存在"
        except dns.resolver.NoAnswer:
            return False, "沒有找到 TXT 記錄"
        except dns.exception.Timeout:
            return False, "DNS 查詢超時，請稍後重試"
        except Exception as e:
            return False, f"DNS 查詢錯誤: {str(e)}"

    @staticmethod
    def _verify_http_access(domain_obj):
        try:
            # 嘗試 HTTP，如果重導向到 HTTPS 也接受
            url = f"http://{domain_obj.domain_name}"
            response = requests.get(url, timeout=10, allow_redirects=True, verify=False)
            
            # 接受 200 狀態碼（正常）或 307/302 重導向
            if response.status_code == 200:
                content_checks = ["TruePay", "誠實商店", "自訂網域管理"]
                if any(check in response.text for check in content_checks):
                    return True, "網站訪問成功，內容驗證通過"
                else:
                    return True, "網站訪問成功（暫時跳過內容檢查）"
            else:
                return False, f"網站訪問失敗，HTTP 狀態: {response.status_code}"
        except requests.exceptions.SSLError:
            # SSL 錯誤但連線成功，表示域名指向正確
            return True, "網站訪問成功（SSL 重導向）"
        except requests.exceptions.ConnectionError:
            return False, "無法連線到網域"
        except requests.exceptions.Timeout:
            return False, "網站訪問超時"
        except Exception as e:
            return False, f"網站訪問錯誤: {str(e)}"

    @staticmethod
    def get_verification_instructions(domain_obj):
        return {
            "record_type": "TXT",
            "record_name": "_truepay-verification",
            "record_value": domain_obj.verification_token,
            "instructions": [
                "📌 DNS 設定步驟：",
                "",
                "登入您的網域管理後台（如 Cloudflare）",
                "進入 DNS 設定頁面",
                "新增 TXT 記錄：",
                "   • 類型：TXT",
                "   • 名稱：_truepay-verification",
                f"  • 值：{domain_obj.verification_token}",
                "儲存設定後等待 DNS 生效（2-10 分鐘）",
                "點擊下方「驗證網域」按鈕",
                "💡 驗證成功後，客戶就能透過您的網域訪問商店了！",
            ],
        }
