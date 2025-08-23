from django.apps import AppConfig


class MerchantAccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "merchant_account"

    def ready(self):
        import merchant_account.signals
