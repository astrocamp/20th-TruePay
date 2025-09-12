"""
測試票券通知邏輯的時間窗口
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from payments.models import OrderItem, Order
import random


class Command(BaseCommand):
    help = '測試票券通知邏輯的時間窗口'

    def handle(self, *args, **options):
        self.stdout.write('[測試] 票券通知時間邏輯測試')
        
        # 建立測試案例
        now = timezone.now()
        test_cases = [
            ('到期前10分鐘', now + timezone.timedelta(minutes=10)),
            ('到期前6分鐘', now + timezone.timedelta(minutes=6)),
            ('到期前5分鐘', now + timezone.timedelta(minutes=5)),
            ('到期前4分鐘', now + timezone.timedelta(minutes=4)),
            ('到期前1分鐘', now + timezone.timedelta(minutes=1)),
            ('剛好到期', now),
            ('過期5分鐘', now - timezone.timedelta(minutes=5)),
            ('過期30分鐘', now - timezone.timedelta(minutes=30)),
            ('過期31分鐘', now - timezone.timedelta(minutes=31)),
            ('過期1小時', now - timezone.timedelta(hours=1)),
        ]
        
        # 找一個基礎訂單
        base_order = Order.objects.filter(status='paid').first()
        if not base_order:
            self.stdout.write('[錯誤] 找不到已付款訂單作為測試基礎')
            return
            
        self.stdout.write('\n=== 通知時機測試 ===')
        self.stdout.write(f'現在時間: {now}')
        self.stdout.write(f'通知邏輯: 到期前6分鐘 ~ 過期後30分鐘')
        self.stdout.write()
        
        for case_name, valid_until in test_cases:
            # 建立模擬票券（不儲存到資料庫）
            test_ticket = OrderItem(
                order=base_order,
                product=base_order.product,
                customer=base_order.customer,
                ticket_code=f'TEST_{random.randint(1000,9999)}',
                status='unused',
                valid_until=valid_until,
                expiry_notification_sent=None
            )
            
            should_notify = test_ticket.should_send_expiry_notification()
            
            # 計算時間差
            time_diff = (valid_until - now).total_seconds() / 60
            
            if time_diff > 0:
                time_desc = f'還有 {time_diff:.1f} 分鐘到期'
            else:
                time_desc = f'已過期 {abs(time_diff):.1f} 分鐘'
                
            result = '[O] 會發送' if should_notify else '[X] 不發送'
            self.stdout.write(f'{case_name:12} | {time_desc:20} | {result}')
        
        self.stdout.write('\n[說明] 正確的行為應該是：')
        self.stdout.write('- 到期前6分鐘開始發送通知')
        self.stdout.write('- 過期後30分鐘內仍可發送')
        self.stdout.write('- 超過30分鐘不再發送通知')
        
        # 測試實際票券
        self.stdout.write('\n=== 現有票券檢查 ===')
        problem_tickets = OrderItem.objects.filter(
            status='unused',
            order__status='paid',
            expiry_notification_sent__isnull=True,
            valid_until__lt=now - timezone.timedelta(hours=1)
        )[:5]
        
        self.stdout.write(f'發現 {problem_tickets.count()} 張超過1小時過期且未通知的票券')
        for ticket in problem_tickets:
            hours_expired = (now - ticket.valid_until).total_seconds() / 3600
            should_notify = ticket.should_send_expiry_notification()
            status = '仍會通知' if should_notify else '不再通知'
            self.stdout.write(f'- {ticket.ticket_code}: 過期 {hours_expired:.1f} 小時, {status}')