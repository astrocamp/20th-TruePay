"""
建立測試票券來驗證到期通知功能
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from payments.models import OrderItem, Order
import random


class Command(BaseCommand):
    help = '建立即將到期的測試票券來驗證通知功能'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=3,
            help='票券將在幾分鐘後到期（預設3分鐘）',
        )

    def handle(self, *args, **options):
        minutes = options['minutes']
        
        # 尋找一個已付款的訂單作為基礎
        order = Order.objects.filter(status='paid').first()
        
        if not order:
            self.stdout.write(self.style.ERROR('找不到已付款的訂單來建立測試票券'))
            return
            
        # 建立測試票券
        test_code = f"TEST{random.randint(1000, 9999)}"
        
        test_ticket = OrderItem.objects.create(
            order=order,
            product=order.product,
            customer=order.customer,
            ticket_code=test_code,
            status='unused',
            valid_until=timezone.now() + timezone.timedelta(minutes=minutes)
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'[成功] 測試票券已建立：{test_ticket.ticket_code}'
            )
        )
        self.stdout.write(f'票券將於 {test_ticket.valid_until} 到期（{minutes}分鐘後）')
        self.stdout.write(f'客戶郵箱：{order.customer.member.email}')
        
        # 檢查是否應該發送通知
        should_notify = test_ticket.should_send_expiry_notification()
        self.stdout.write(f'應該發送通知：{should_notify}')
        
        if minutes <= 5:
            self.stdout.write('[提示] 票券將在5分鐘內到期，系統會自動發送通知')
        else:
            self.stdout.write('[提示] 票券到期時間超過5分鐘，需要等到到期前5分鐘才會發送通知')