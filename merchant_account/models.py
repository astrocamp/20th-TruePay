from django.db import models, transaction
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.utils import timezone
import re
import secrets


# Create your models here.
class Merchant(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ("pending", "待審核"),
        ("approved", "已通過"),
        ("rejected", "已拒絕"),
        ("suspended", "已暫停"),
    ]

    member = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="會員帳號",
    )
    ShopName = models.CharField(max_length=50, null=False)
    UnifiedNumber = models.CharField(max_length=8, null=False)
    NationalNumber = models.CharField(max_length=10, null=False)
    Name = models.CharField(max_length=30, null=False)
    Address = models.CharField(max_length=50, null=False)
    Cellphone = models.CharField(max_length=15, null=False)
    subdomain = models.SlugField(max_length=50, unique=True, null=False, blank=False)

    # 商家審核相關欄位
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default="pending",
        verbose_name="審核狀態",
        help_text="商家身份驗證狀態",
    )
    verified_at = models.DateTimeField(
        null=True, blank=True, verbose_name="通過審核時間"
    )
    rejection_reason = models.TextField(
        blank=True, verbose_name="拒絕原因", help_text="審核不通過時的原因說明"
    )
    verification_documents = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="驗證文件",
        help_text="儲存審核相關文件的元資料",
    )
    subdomain_change_count = models.PositiveIntegerField(
        default=0,
        verbose_name="修改次數",
        help_text="本年度修改次數",
    )
    last_subdomain_change = models.DateTimeField(
        null=True, blank=True, verbose_name="上次修改時間"
    )
    subdomain_history = models.JSONField(
        default=list, verbose_name="修改歷史", help_text="所有 subdomain 修改紀錄"
    )
    STORE_TEMPLATE_CHOICES = [
        ("modern_light", "modern_light"),
        ("modern", "modern"),
        ("tech", "tech"),
        ("handcraft", "handcraft"),
        ("vintage", "vintage"),
    ]
    store_template_id = models.CharField(
        max_length=20,
        choices=STORE_TEMPLATE_CHOICES,
        default="modern",
        verbose_name="商店模板風格",
        help_text="選擇商店頁面的視覺風格樣式",
    )

    def __str__(self):
        return self.ShopName

    max_subdomains_change_per_year = 2
    subdomain_change_cooldown_days = 30

    def can_change_subdomain(self):
        if self.subdomain_change_count >= self.max_subdomains_change_per_year:
            return False, f"已達年度修改上限({self.max_subdomains_change_per_year}次)"
        if self.last_subdomain_change:
            days_since_last = (timezone.now() - self.last_subdomain_change).days
            if days_since_last < self.subdomain_change_cooldown_days:
                remaining_days = self.subdomain_change_cooldown_days - days_since_last
                return False, f"請等待{remaining_days}天後再行修改"
        return True, "可以修改"

    @classmethod
    def validate_subdomain_format(cls, subdomain):
        if len(subdomain) < 3:
            return False, "子網域名稱至少需要 3 個字元"
        if len(subdomain) > 30:
            return False, "子網域名稱不能超過 30 個字元"

        if not re.match(r"^[a-zA-Z0-9-]+$", subdomain):
            return False, "只能使用英文字母、數字和連字號"
        if subdomain.startswith("-") or subdomain.endswith("-"):
            return False, "不能以連字號開頭或結尾"
        if "--" in subdomain:
            return False, "不能有連續的連字號"
        return True, "格式正確"

    def change_subdomain(self, new_subdomain, reason="商家主動修改"):

        can_change, message = self.can_change_subdomain()
        if not can_change:
            raise ValueError(message)

        is_valid, format_message = self.validate_subdomain_format(new_subdomain)
        if not is_valid:
            raise ValueError(format_message)

        if Merchant.objects.filter(subdomain=new_subdomain).exists():
            raise ValueError("此子網域名稱已被使用")

        with transaction.atomic():
            old_subdomain = self.subdomain
            history_record = {
                "old_subdomain": old_subdomain,
                "new_subdomain": new_subdomain,
                "changed_at": timezone.now().isoformat(),
                "reason": reason,
            }
            self.subdomain_history.append(history_record)
            self.subdomain = new_subdomain
            self.subdomain_change_count += 1
            self.last_subdomain_change = timezone.now()

            self.save(
                update_fields=[
                    "subdomain_history",
                    "subdomain",
                    "subdomain_change_count",
                    "last_subdomain_change",
                ]
            )

            SubdomainRedirect.create_redirect(
                old_subdomain=old_subdomain, new_subdomain=new_subdomain, merchant=self
            )

        return True

    def reset_yearly_change_count(self):
        self.subdomain_change_count = 0
        self.save(update_fields=["subdomain_change_count"])

    # 商家審核相關方法
    def is_verified(self):
        """檢查商家是否已通過審核"""
        return self.verification_status == "approved"

    def can_operate(self):
        """檢查商家是否可以進行營業活動"""
        return self.verification_status == "approved" and self.member.is_active

    def approve_verification(self, admin_user=None):
        """通過商家審核"""
        self.verification_status = "approved"
        self.verified_at = timezone.now()
        self.rejection_reason = ""
        self.save(
            update_fields=["verification_status", "verified_at", "rejection_reason"]
        )
        # 可以在這裡加入發送通知郵件的邏輯
        print(f"✅ 商家 {self.ShopName} 已通過審核")

    def reject_verification(self, reason="", admin_user=None):
        """拒絕商家審核"""
        self.verification_status = "rejected"
        self.rejection_reason = reason
        self.verified_at = None
        self.save(
            update_fields=["verification_status", "rejection_reason", "verified_at"]
        )
        # 可以在這裡加入發送通知郵件的邏輯
        print(f"❌ 商家 {self.ShopName} 審核被拒絕：{reason}")

    def suspend_merchant(self, reason=""):
        """暫停商家營業"""
        self.verification_status = "suspended"
        self.rejection_reason = reason
        self.save(update_fields=["verification_status", "rejection_reason"])

        print(f"⚠️ 商家 {self.ShopName} 已被暫停營業：{reason}")

    def get_verification_status_display_with_icon(self):
        """取得帶圖標的審核狀態顯示"""
        status_icons = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌",
            "suspended": "⚠️",
        }
        icon = status_icons.get(self.verification_status, "❓")
        return f"{icon} {self.get_verification_status_display()}"

    def check_auto_approval_eligibility(self):
        """檢查是否符合自動審核條件，返回 (是否符合, 具體檢查結果)"""
        checks = []

        # 如果關閉自動審核功能
        if not getattr(settings, "ENABLE_AUTO_MERCHANT_APPROVAL", True):
            return False, [
                {"field": "系統", "status": "disabled", "message": "自動審核功能已關閉"}
            ]

        # 條件1：統一編號格式檢查（8位數字）
        if (
            not self.UnifiedNumber
            or len(self.UnifiedNumber) != 8
            or not self.UnifiedNumber.isdigit()
        ):
            checks.append(
                {
                    "field": "UnifiedNumber",
                    "status": "failed",
                    "message": "統一編號格式不正確，需要8位數字",
                }
            )
        else:
            checks.append(
                {
                    "field": "UnifiedNumber",
                    "status": "passed",
                    "message": "統一編號格式正確",
                }
            )

        # 條件2：身分證字號格式檢查
        if not re.match(r"^[A-Z][12][0-9]{8}$", self.NationalNumber):
            checks.append(
                {
                    "field": "NationalNumber",
                    "status": "failed",
                    "message": "身分證字號格式不正確（格式：A123456789）",
                }
            )
        else:
            checks.append(
                {
                    "field": "NationalNumber",
                    "status": "passed",
                    "message": "身分證字號格式正確",
                }
            )

        # 條件3：手機號碼格式檢查
        if not re.match(r"^09[0-9]{8}$", self.Cellphone):
            checks.append(
                {
                    "field": "Cellphone",
                    "status": "failed",
                    "message": "手機號碼格式不正確（格式：09xxxxxxxx）",
                }
            )
        else:
            checks.append(
                {
                    "field": "Cellphone",
                    "status": "passed",
                    "message": "手機號碼格式正確",
                }
            )

        # 條件4：檢查是否有重複的統一編號
        duplicate_unified = (
            Merchant.objects.exclude(pk=self.pk)
            .filter(UnifiedNumber=self.UnifiedNumber)
            .exists()
        )
        if duplicate_unified:
            checks.append(
                {
                    "field": "UnifiedNumber",
                    "status": "failed",
                    "message": "統一編號已被其他商家使用",
                }
            )

        # 條件5：檢查商店名稱長度
        if len(self.ShopName) < 2:
            checks.append(
                {
                    "field": "ShopName",
                    "status": "failed",
                    "message": "商店名稱過短，至少需要2個字元",
                }
            )
        else:
            checks.append(
                {
                    "field": "ShopName",
                    "status": "passed",
                    "message": "商店名稱長度符合要求",
                }
            )

        # 條件6：檢查地址是否完整
        if not self.Address or len(self.Address) < 5:
            checks.append(
                {
                    "field": "Address",
                    "status": "failed",
                    "message": "地址資訊不完整，至少需要5個字元",
                }
            )
        else:
            checks.append(
                {"field": "Address", "status": "passed", "message": "地址資訊完整"}
            )

        # 條件7：檢查email域名是否在白名單中（如果有設定）
        if (
            hasattr(settings, "AUTO_APPROVE_EMAIL_DOMAINS")
            and settings.AUTO_APPROVE_EMAIL_DOMAINS
        ):
            email_domain = self.member.email.split("@")[1].lower()
            if email_domain not in [
                domain.lower() for domain in settings.AUTO_APPROVE_EMAIL_DOMAINS
            ]:
                checks.append(
                    {
                        "field": "email",
                        "status": "failed",
                        "message": f"Email域名 {email_domain} 不在自動審核白名單中",
                    }
                )
            else:
                checks.append(
                    {
                        "field": "email",
                        "status": "passed",
                        "message": "Email域名在允許列表中",
                    }
                )

        # 判斷是否全部通過
        all_passed = all(
            check["status"] == "passed"
            for check in checks
            if check["status"] != "disabled"
        )
        return all_passed, checks

    def attempt_auto_approval(self):
        """嘗試自動審核"""
        if self.verification_status not in ["pending", "rejected"]:
            return False, "商家狀態不允許自動審核"

        eligible, checks = self.check_auto_approval_eligibility()

        if eligible:
            old_status = self.verification_status
            self.verification_status = "approved"
            self.verified_at = timezone.now()
            self.rejection_reason = ""
            self.save(
                update_fields=["verification_status", "verified_at", "rejection_reason"]
            )

            print(
                f"✅ 商家 {self.ShopName} 已自動通過審核（從 {old_status} 變更為 approved）"
            )
            return True, "自動審核通過"
        else:
            failed_checks = [check for check in checks if check["status"] == "failed"]
            reasons = [check["message"] for check in failed_checks]
            rejection_reason = "自動審核未通過：" + "；".join(reasons)

            if self.verification_status == "pending":
                self.verification_status = "rejected"
                self.rejection_reason = rejection_reason
                self.save(update_fields=["verification_status", "rejection_reason"])

            print(
                f"⏳ 商家 {self.ShopName} 自動審核未通過，共 {len(failed_checks)} 項不符合"
            )
            return False, rejection_reason

    def get_verification_issues(self):
        """取得詳細的審核問題列表（用於前端顯示）"""
        eligible, checks = self.check_auto_approval_eligibility()
        return {
            "is_approved": self.verification_status == "approved",
            "can_auto_approve": eligible,
            "checks": checks,
        }


class SubdomainRedirect(models.Model):
    old_subdomain = models.CharField(max_length=50, verbose_name="舊子網域")
    new_subdomain = models.CharField(max_length=50, verbose_name="新子網域")
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="subdomain_redirects",
        verbose_name="商家",
    )
    is_active = models.BooleanField(default=True, verbose_name="啟用中")
    redirect_type = models.CharField(
        max_length=20,
        choices=[("301", "永久重導向"), ("302", "暫時重導向")],
        default="301",
        verbose_name="重導向類型",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="過期時間")
    redirect_count = models.PositiveIntegerField(default=0, verbose_name="重導向次數")
    last_used = models.DateTimeField(null=True, blank=True, verbose_name="最後使用時間")

    class Meta:
        verbose_name = "子網域重導向"
        verbose_name_plural = "子網域重導向"
        unique_together = ["old_subdomain", "merchant"]

    def __str__(self):
        return f"{self.old_subdomain} → {self.new_subdomain}"

    @classmethod
    def create_redirect(cls, old_subdomain, new_subdomain, merchant, duration_days=30):
        expires_at = timezone.now() + timezone.timedelta(days=duration_days)
        redirect = cls.objects.create(
            old_subdomain=old_subdomain,
            new_subdomain=new_subdomain,
            merchant=merchant,
            expires_at=expires_at,
        )
        return redirect

    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at

    def use_redirect(self):
        self.redirect_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=["redirect_count", "last_used"])
