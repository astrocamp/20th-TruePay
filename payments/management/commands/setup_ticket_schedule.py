"""
Django 管理命令：設定票券到期通知排程任務
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = '設定票券到期通知的 Celery Beat 排程任務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='重置所有票券相關的排程任務',
        )
        
        parser.add_argument(
            '--list',
            action='store_true',
            help='列出所有票券相關的排程任務',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_tasks()
            return
            
        if options['reset']:
            self.reset_tasks()
            
        self.setup_tasks()
        
    def list_tasks(self):
        """列出所有票券相關的排程任務"""
        self.stdout.write(self.style.SUCCESS('=== 票券相關排程任務列表 ==='))
        
        tasks = PeriodicTask.objects.filter(
            name__in=[
                'check-ticket-expiry-every-minute',
                'cleanup-expired-tickets-hourly',
                'daily-ticket-report'
            ]
        )
        
        for task in tasks:
            status = "啟用" if task.enabled else "停用"
            self.stdout.write(f"[任務] {task.name}")
            self.stdout.write(f"   任務: {task.task}")
            self.stdout.write(f"   排程: {task.crontab}")
            self.stdout.write(f"   狀態: {status}")
            self.stdout.write(f"   最後執行: {task.last_run_at or '尚未執行'}")
            self.stdout.write("")
            
    def reset_tasks(self):
        """重置所有票券相關的排程任務"""
        self.stdout.write(self.style.WARNING('[重置] 票券排程任務...'))
        
        task_names = [
            'check-ticket-expiry-every-minute',
            'cleanup-expired-tickets-hourly', 
            'daily-ticket-report'
        ]
        
        deleted_count = PeriodicTask.objects.filter(name__in=task_names).delete()[0]
        self.stdout.write(f"[成功] 已刪除 {deleted_count} 個舊任務")
        
    def setup_tasks(self):
        """設定排程任務"""
        self.stdout.write(self.style.SUCCESS('[設定] 票券到期通知排程任務...'))
        
        # 1. 每分鐘檢查票券到期
        every_minute, created = CrontabSchedule.objects.get_or_create(
            minute='*',
            hour='*',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_1, created_1 = PeriodicTask.objects.get_or_create(
            name='check-ticket-expiry-every-minute',
            defaults={
                'crontab': every_minute,
                'task': 'payments.check_ticket_expiry',
                'enabled': True,
                'kwargs': json.dumps({}),
                'expires': timezone.now() + timezone.timedelta(seconds=55),
            }
        )
        
        if created_1:
            self.stdout.write("[成功] 建立每分鐘票券到期檢查任務")
        else:
            self.stdout.write("[資訊] 每分鐘票券到期檢查任務已存在")
            
        # 2. 每小時清理過期票券
        every_hour, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='*',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_2, created_2 = PeriodicTask.objects.get_or_create(
            name='cleanup-expired-tickets-hourly',
            defaults={
                'crontab': every_hour,
                'task': 'payments.cleanup_expired_tickets',
                'enabled': True,
                'kwargs': json.dumps({}),
            }
        )
        
        if created_2:
            self.stdout.write("[成功] 建立每小時過期票券清理任務")
        else:
            self.stdout.write("[資訊] 每小時過期票券清理任務已存在")
            
        # 3. 每日統計報表
        daily_report, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='23',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_3, created_3 = PeriodicTask.objects.get_or_create(
            name='daily-ticket-report',
            defaults={
                'crontab': daily_report,
                'task': 'payments.send_daily_ticket_report',
                'enabled': True,
                'kwargs': json.dumps({}),
            }
        )
        
        if created_3:
            self.stdout.write("[成功] 建立每日統計報表任務")
        else:
            self.stdout.write("[資訊] 每日統計報表任務已存在")
            
        self.stdout.write(self.style.SUCCESS('\n[完成] 票券排程任務設定完成！'))
        self.stdout.write("[說明] 使用方法：")
        self.stdout.write("   • 啟動 Celery Worker: celery -A truepay worker --loglevel=info")
        self.stdout.write("   • 啟動 Celery Beat: celery -A truepay beat --loglevel=info")
        self.stdout.write("   • 查看任務狀態: python manage.py setup_ticket_schedule --list")
        self.stdout.write("   • 重置任務: python manage.py setup_ticket_schedule --reset")