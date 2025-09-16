import cloudflare as CloudFlare
import dns.resolver
import dns.exception
from django.conf import settings
from django.utils import timezone
from .models import MerchantOwnDomain
import logging

logger = logging.getLogger(__name__)


class CloudflareService:
    def __init__(self):
        self.cf = CloudFlare.CloudFlare(token=settings.CLOUDFLARE_API_TOKEN)
        self.zone_id = settings.CLOUDFLARE_ZONE_ID

    def setup_merchant_domain(self, merchant_domain):
        # 替商家設定自訂網域的CNAME紀錄
        try:
            target_subdomain = (
                f"{merchant_domain.merchant.subdomain}.{settings.BASE_DOMAIN}"
            )

            dns_record = {
                "type": "CNAME",
                "name": merchant_domain.domain_name,
                "content": target_subdomain,
                "ttl": 300,
            }
            result = self.cf.zones.dns_records.post(self.zone_id, data=dns_record)

            merchant_domain.cloudflare_record_id = result["id"]
            merchant_domain.cname_target = target_subdomain
            merchant_domain.is_verified = True
            merchant_domain.verified_at = timezone.now()
            merchant_domain.save()

            return True, f"成功設定 {merchant_domain.domain_name} → {target_subdomain}"
        except Exception as e:
            logger.error(f"Cloudflare DNS 設定失敗: {str(e)}")
            return False, f"設定失敗: {str(e)}"

    def verify_cname_record(self, merchant_domain):
        # 驗證CNAME紀錄
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 10

            answers = resolver.resolve(merchant_domain.domain_name, "CNAME")
            expected_target = (
                f"{merchant_domain.merchant.subdomain}.{settings.BASE_DOMAIN}"
            )

            for answer in answers:
                cname_target = str(answer.target).rstrip(".")
                if cname_target == expected_target:
                    return True, "CNAME 記錄驗證成功"
            return False, f"CNAME 指向錯誤，應該指向: {expected_target}"
        except dns.resolver.NXDOMAIN:
            return False, "網域不存在"
        except dns.resolver.NoAnswer:
            return False, "沒有找到 CNAME 記錄"
        except Exception as e:
            return False, f"DNS 查詢錯誤: {str(e)}"

    def delete_dns_record(self, merchant_domain):
        # 刪除DNS紀錄
        try:
            if merchant_domain.cloudflare_record_id:
                self.cf.zones.dns_records.delete(
                    self.zone_id, merchant_domain.cloudflare_record_id
                )
            return True, "DNS 記錄已刪除"
        except Exception as e:
            return False, f"刪除失敗: {str(e)}"

    def get_setup_instructions(self, merchant_domain):
        # 商家設定說明
        target_subdomain = (
            f"{merchant_domain.merchant.subdomain}.{settings.BASE_DOMAIN}"
        )
        return {
            "method": "CNAME",
            "domain": merchant_domain.domain_name,
            "target": target_subdomain,
            "instructions": [
                "🎯 自動 DNS 設定",
                "",
                "我們將自動為您設定以下 DNS 記錄：",
                f"   類型：CNAME",
                f"   名稱：{merchant_domain.domain_name}",
                f"   指向：{target_subdomain}",
                "",
                "✅ 優點：",
                "• 自動 SSL 憑證（HTTPS）",
                "• 登入資料互通",
                "• 無需手動 DNS 設定",
                "",
                "點擊下方「自動設定」按鈕即可完成！",
            ],
        }
