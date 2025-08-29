from django.core.management.base import BaseCommand
from merchant_account.models import Merchant


class Command(BaseCommand):
    help = "現有商家明文密碼加密"

    def handle(self, *args, **options):
        merchants = Merchant.objects.all()
        update_count = 0

        for merchant in merchants:
            if not merchant.Password.startswith("pbkdf2_"):
                raw_password = merchant.Password
                merchant.set_password(raw_password)
                merchant.save()
                update_count += 1
                self.stdout.write(self.style.SUCCESS(f"已加密{merchant.Email}的密碼"))
            else:
                self.stdout.write(f"{merchant.Email}的商家已經加密過")
        self.stdout.write(self.style.SUCCESS(f"已加密{update_count}個商家"))
