from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError as EmailValidationError
import logging

from .models import Member
from customers_account.models import Customer

logger = logging.getLogger(__name__)

GOOGLE_PROVIDER = "google"
CUSTOMER_TYPE = "customer"


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def _get_email_from_sociallogin(self, sociallogin):
        """從社群登入資料中取得並驗證 email"""
        try:
            extra_data = sociallogin.account.extra_data

            email = extra_data.get("email")
            if not email or not isinstance(email, str):
                return None

            # 驗證 email 格式
            email = email.strip().lower()
            validator = EmailValidator()
            validator(email)

            return email

        except (EmailValidationError, AttributeError, TypeError):
            return None

    def _get_name_from_sociallogin(self, sociallogin):
        """從社群登入資料中取得姓名"""
        try:
            extra_data = sociallogin.account.extra_data

            name = extra_data.get("name", "")
            if not name or not isinstance(name, str):
                return ""

            return name.strip()

        except (AttributeError, TypeError):
            return ""

    def _find_customer_with_social_info(self, email):
        """一次查詢取得消費者帳號及其 Google 社群帳號連結狀況"""
        try:
            member = (
                Member.objects.prefetch_related("socialaccount_set")
                .filter(email=email, member_type=CUSTOMER_TYPE)
                .first()
            )

            if not member:
                return None, False

            # 檢查是否已有 Google 連結
            has_google_account = any(
                social.provider == GOOGLE_PROVIDER
                for social in member.socialaccount_set.all()
            )

            return member, has_google_account

        except Exception:
            return None, False

    def pre_social_login(self, request, sociallogin):
        """
        在社群登入之前檢查是否有相同 email 的用戶。如果有，就連結現有帳號；如果沒有，允許創建新帳號
        """

        if sociallogin.is_existing:
            return

        email = self._get_email_from_sociallogin(sociallogin)
        if not email:
            return

        # 查詢消費者帳號及 Google 連結狀況
        existing_customer, has_google_account = self._find_customer_with_social_info(
            email
        )

        if existing_customer and not has_google_account:
            # 還沒有 Google 連結，連結現有用戶
            try:
                sociallogin.connect(request, existing_customer)
                logger.info(f"成功連結現有消費者帳號: {email}")
                return
            except IntegrityError as e:
                logger.error(f"帳號連結失敗 - 資料完整性錯誤: {e}, email: {email}")
                raise ValidationError("帳號連結時發生資料錯誤，請稍後再試或聯繫客服")
            except ValidationError as e:
                logger.error(f"帳號連結失敗 - 驗證錯誤: {e}, email: {email}")
                raise ValidationError(f"帳號驗證失敗: {str(e)}")
            except Exception as e:
                logger.error(f"帳號連結失敗 - 未知錯誤: {e}, email: {email}")
                raise ValidationError("系統異常，請稍後再試或聯繫客服")

        existing_merchant = (
            Member.objects.filter(email=email)
            .exclude(member_type=CUSTOMER_TYPE)
            .first()
        )

        if existing_merchant:
            sociallogin.state["process"] = "signup"
            user = self.save_user(request, sociallogin)
            sociallogin.connect(request, user)
            return

    def save_user(self, request, sociallogin, form=None):
        """
        當創建新的社群登入用戶時，同時創建對應的 Customer 記錄
        """
        email = self._get_email_from_sociallogin(sociallogin)
        if not email:
            raise ValidationError("無法從 Google 帳號取得有效的 email 地址")

        name = self._get_name_from_sociallogin(sociallogin)

        try:
            with transaction.atomic():
                # 創建 Member
                user = super().save_user(request, sociallogin, form)

                if not user or not user.pk:
                    raise ValidationError("用戶創建失敗")

                user.member_type = CUSTOMER_TYPE
                user.save(update_fields=["member_type"])

                try:
                    customer, created = Customer.objects.get_or_create(
                        member=user,
                        defaults={
                            "name": name,
                        },
                    )
                except IntegrityError:
                    customer = Customer.objects.filter(member=user).first()
                    if not customer:
                        raise ValidationError("Customer 記錄創建失敗")

                return user

        except ValidationError:
            raise
        except IntegrityError as e:
            raise ValidationError(f"資料庫完整性錯誤: {str(e)}")
        except Exception as e:
            raise ValidationError(f"創建用戶時發生未預期的錯誤: {str(e)}")
