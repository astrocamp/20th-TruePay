from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from customers_account.models import Customer


class Command(BaseCommand):
    help = "更新現有客戶資料"

    def handle(self, *args, **options):
        updated_count = 0
        customers = Customer.objects.all()

        for customer in customers:
            new_username = f"customer_{customer.email}"
            try:
                old_user = User.objects.get(username=customer.email)
                if not User.objects.filter(username=new_username).exists():
                    old_user.username = new_username
                    old_user.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"已經更新{customer.email}的顧客格式")
                    )
                else:
                    old_user.delete()
                    self.stdout.write(f"已刪出{customer.email}的舊格式")
            except User.DoesNotExist:
                if not User.objects.filter(username=new_username).exists():
                    User.objects.create(
                        username=f"customer_{customer.email}",
                        email=customer.email,
                        first_name=customer.name,
                        is_active=customer.account_status == "active",
                        password=customer.password,
                    )
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"已建立{customer.email}的紀錄")
                    )
        self.stdout.write(
            self.style.SUCCESS(f"總共處理了 {updated_count} 個customer的記錄")
        )
