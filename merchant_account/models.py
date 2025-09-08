from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.utils import timezone
import re


# Create your models here.
class Merchant(models.Model):
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

        old_subdomain = self.subdomain
        history_record = {
            "old_subdomain": old_subdomain,
            "new_subdomain": new_subdomain,
            "changed_at": timezone.now().isoformat(),
            "reason": reason,
        }
        if not self.subdomain_history:
            self.subdomain_history = []
        self.subdomain_history.append(history_record)
        self.subdomain = new_subdomain
        self.subdomain_change_count += 1
        self.last_subdomain_change = timezone.now()
        self.save()

        SubdomainRedirect.create_redirect(
            old_subdomain=old_subdomain, new_subdomain=new_subdomain, merchant=self
        )

        return True

    def reset_yearly_change_count(self):
        self.subdomain_change_count = 0
        self.save(update_fields=["subdomain_change_count"])


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
