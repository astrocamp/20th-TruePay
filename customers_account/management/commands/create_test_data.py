from django.core.management.base import BaseCommand
from django.utils import timezone
from customers_account.models import Customer
from newebpay.models import Payment
import uuid


class Command(BaseCommand):
    help = '建立測試用的付款記錄資料'

    def handle(self, *args, **options):
        # 創建測試用戶（如果不存在）
        customer, created = Customer.objects.get_or_create(
            email='test@example.com',
            defaults={
                'name': '測試用戶',
                'id_number': 'A123456789',
                'birth_date': '1990-01-01',
                'phone': '0912345678',
                'email_verified': True,
                'account_status': 'active'
            }
        )
        
        if created:
            customer.set_password('test123')
            customer.save()
            self.stdout.write(self.style.SUCCESS(f'創建測試用戶: {customer.email}'))
        else:
            self.stdout.write(f'測試用戶已存在: {customer.email}')

        # 建立測試付款記錄
        test_payments = [
            {
                'merchant_order_no': 'T1-LOL-WORLDS-2024-001',
                'amt': 2500,
                'item_desc': 'T1 LOL世界大賽門票 - VIP席位',
                'email': customer.email,
                'customer_name': customer.name,
                'customer_phone': customer.phone,
                'status': 'paid',
                'payment_type': '信用卡',
                'pay_time': timezone.now(),
                'trade_no': 'TXN' + str(uuid.uuid4())[:8].upper(),
            },
            {
                'merchant_order_no': 'MUSIC-FESTIVAL-2024-001',
                'amt': 1800,
                'item_desc': '台北音樂節門票 - 一般席位',
                'email': customer.email,
                'customer_name': customer.name,
                'customer_phone': customer.phone,
                'status': 'paid',
                'payment_type': 'LinePay',
                'pay_time': timezone.now() - timezone.timedelta(days=7),
                'trade_no': 'TXN' + str(uuid.uuid4())[:8].upper(),
            },
            {
                'merchant_order_no': 'CONCERT-TAYLOR-2024-001',
                'amt': 4500,
                'item_desc': 'Taylor Swift演唱會門票 - 搖滾區',
                'email': customer.email,
                'customer_name': customer.name,
                'customer_phone': customer.phone,
                'status': 'paid',
                'payment_type': '信用卡',
                'pay_time': timezone.now() - timezone.timedelta(days=15),
                'trade_no': 'TXN' + str(uuid.uuid4())[:8].upper(),
            }
        ]

        for payment_data in test_payments:
            payment, created = Payment.objects.get_or_create(
                merchant_order_no=payment_data['merchant_order_no'],
                defaults=payment_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'創建測試付款記錄: {payment.item_desc}')
                )
            else:
                self.stdout.write(f'付款記錄已存在: {payment.item_desc}')

        self.stdout.write(
            self.style.SUCCESS('測試資料建立完成！')
        )
        self.stdout.write(
            self.style.WARNING('測試帳號: test@example.com / 密碼: test123')
        )