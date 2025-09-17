"""
診斷票券通知系統的詳細狀況
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from payments.models import OrderItem
import traceback


class Command(BaseCommand):
    help = '診斷票券通知系統的詳細狀況'

    def handle(self, *args, **options):
        self.stdout.write('[診斷] 開始票券通知系統診斷...')
        
        # 1. 基本統計
        self.stdout.write('\n=== 基本統計 ===')
        total_tickets = OrderItem.objects.count()
        unused_tickets = OrderItem.objects.filter(status='unused').count()
        paid_unused = OrderItem.objects.filter(status='unused', order__status='paid').count()
        
        self.stdout.write(f'總票券數: {total_tickets}')
        self.stdout.write(f'未使用票券: {unused_tickets}')
        self.stdout.write(f'已付款未使用票券: {paid_unused}')
        
        # 2. 檢查需要通知的票券
        self.stdout.write('\n=== 需要通知的票券 ===')
        candidates = OrderItem.objects.filter(
            status='unused',
            order__status='paid',
            valid_until__isnull=False,
            expiry_notification_sent__isnull=True,
            customer__isnull=False,
            customer__member__email__isnull=False,
        ).order_by('valid_until')[:10]
        
        self.stdout.write(f'符合基本條件的候選票券: {candidates.count()}')
        
        for ticket in candidates:
            should_notify = ticket.should_send_expiry_notification()
            self.stdout.write(
                f'- {ticket.ticket_code}: '
                f'到期={ticket.valid_until}, '
                f'應通知={should_notify}, '
                f'客戶={ticket.customer.member.email}'
            )
            
            if should_notify:
                self.stdout.write(f'  [測試] 嘗試發送通知給 {ticket.ticket_code}...')
                try:
                    result = ticket.send_expiry_notification()
                    self.stdout.write(f'  [結果] 發送成功: {result}')
                except Exception as e:
                    self.stdout.write(f'  [錯誤] 發送失敗: {str(e)}')
                    self.stdout.write(f'  [詳細] {traceback.format_exc()}')
        
        # 3. 檢查已發送通知的票券
        self.stdout.write('\n=== 已發送通知的票券 ===')
        notified = OrderItem.objects.filter(
            expiry_notification_sent__isnull=False
        ).order_by('-expiry_notification_sent')[:5]
        
        self.stdout.write(f'已發送通知的票券總數: {notified.count()}')
        for ticket in notified:
            self.stdout.write(
                f'- {ticket.ticket_code}: '
                f'通知時間={ticket.expiry_notification_sent}, '
                f'到期時間={ticket.valid_until}'
            )
        
        # 4. 測試郵件連線
        self.stdout.write('\n=== 郵件系統測試 ===')
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            self.stdout.write(f'郵件服務商: {settings.EMAIL_PROVIDER}')
            self.stdout.write(f'SMTP 主機: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
            self.stdout.write(f'TLS 加密: {settings.EMAIL_USE_TLS}')
            
            # 嘗試發送測試郵件
            test_result = send_mail(
                subject='TruePay 系統測試',
                message='這是票券通知系統的測試郵件',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['test@example.com'],
                fail_silently=False,
            )
            self.stdout.write(f'測試郵件發送結果: {test_result}')
            
        except Exception as e:
            self.stdout.write(f'[郵件錯誤] {str(e)}')
            self.stdout.write(f'[詳細錯誤] {traceback.format_exc()}')
        
        self.stdout.write('\n[完成] 診斷完成')