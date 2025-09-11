"""
票券到期通知管理命令
用於發送即將到期票券的郵件通知
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from payments.models import OrderItem
import logging

# 設定日誌
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '發送票券到期通知郵件（到期前 5 分鐘）'

    def add_arguments(self, parser):
        """新增命令參數"""
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模擬執行，不實際發送郵件',
        )
        parser.add_argument(
            '--minutes',
            type=int,
            default=5,
            help='到期前幾分鐘發送通知（預設: 5 分鐘）',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細執行過程',
        )

    def handle(self, *args, **options):
        """執行命令的主要邏輯"""
        dry_run = options['dry_run']
        minutes_before = options['minutes']
        verbose = options['verbose']
        
        start_time = timezone.now()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('[模擬] 模擬執行模式 - 不會實際發送郵件')
            )
        
        self.stdout.write(
            f'[開始] 開始執行票券到期通知任務 - {start_time.strftime("%Y-%m-%d %H:%M:%S")}'
        )
        self.stdout.write(f'[設定] 通知時間點: 到期前 {minutes_before} 分鐘')
        
        try:
            if dry_run:
                result = self.simulate_notifications(minutes_before, verbose)
            else:
                result = OrderItem.send_all_expiry_notifications()
            
            self.display_results(result)
            
        except Exception as e:
            error_msg = f'執行失敗: {str(e)}'
            self.stdout.write(self.style.ERROR(f'[錯誤] {error_msg}'))
            logger.error(error_msg, exc_info=True)
            raise CommandError(error_msg)
        
        end_time = timezone.now()
        execution_time = (end_time - start_time).total_seconds()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'[完成] 任務執行完成 - 耗時 {execution_time:.2f} 秒'
            )
        )

    def simulate_notifications(self, minutes_before, verbose):
        """模擬執行通知發送"""
        # 查找所有需要發送通知的票券
        tickets_to_notify = OrderItem.objects.filter(
            status='unused',
            order__status='paid',
            valid_until__isnull=False,
            expiry_notification_sent__isnull=True,
            customer__isnull=False,
            customer__member__email__isnull=False,
        ).select_related(
            'customer', 
            'customer__member', 
            'product', 
            'product__merchant',
            'order'
        )
        
        notifications_sent = 0
        total_checked = 0
        
        for ticket in tickets_to_notify:
            total_checked += 1
            if ticket.should_send_expiry_notification(minutes_before):
                notifications_sent += 1
                if verbose:
                    self.stdout.write(
                        f'[模擬] 發送通知給: {ticket.customer.member.email} '
                        f'(票券: {ticket.ticket_code})'
                    )
        
        return {
            'total_checked': total_checked,
            'notifications_sent': notifications_sent,
            'errors_count': 0,
            'success_rate': 100.0 if notifications_sent > 0 else 0
        }

    def display_results(self, result):
        """顯示執行結果"""
        self.stdout.write('\n[統計] 執行結果統計:')
        self.stdout.write('=' * 40)
        
        self.stdout.write(f'[檢查] 檢查票券數量: {result["total_checked"]}')
        self.stdout.write(f'[發送] 發送通知數量: {result["notifications_sent"]}')
        
        if result['errors_count'] > 0:
            self.stdout.write(
                self.style.ERROR(f'[失敗] 發送失敗數量: {result["errors_count"]}')
            )
        
        success_rate = result['success_rate']
        if success_rate == 100:
            style = self.style.SUCCESS
            prefix = '[成功]'
        elif success_rate >= 80:
            style = self.style.WARNING
            prefix = '[警告]'
        else:
            style = self.style.ERROR
            prefix = '[錯誤]'
        
        self.stdout.write(
            style(f'{prefix} 成功率: {success_rate:.1f}%')
        )
        
        if result['notifications_sent'] == 0:
            self.stdout.write(
                self.style.WARNING('[提示] 目前沒有需要發送通知的票券')
            )