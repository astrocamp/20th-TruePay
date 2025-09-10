from django.core.management.base import BaseCommand
from django.utils import timezone
from payments.models import OrderItem
import random


class Command(BaseCommand):
    help = '為現有沒有 ticket_code 的票券生成代碼'

    def handle(self, *args, **options):
        # 找出所有沒有 ticket_code 或 ticket_code 為空的票券
        tickets_without_code = OrderItem.objects.filter(
            ticket_code__isnull=True
        ).union(
            OrderItem.objects.filter(ticket_code='')
        )
        
        count = tickets_without_code.count()
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('所有票券都已有 ticket_code，無需處理')
            )
            return
        
        self.stdout.write(f'找到 {count} 張沒有 ticket_code 的票券')
        
        updated_count = 0
        for ticket in tickets_without_code:
            # 生成唯一的 ticket_code
            while True:
                timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
                random_suffix = str(random.randint(1000, 9999))
                ticket_code = f"TKT{ticket.id:08d}{timestamp}{random_suffix}"
                
                # 檢查是否重複
                if not OrderItem.objects.filter(ticket_code=ticket_code).exists():
                    ticket.ticket_code = ticket_code
                    ticket.save(update_fields=['ticket_code'])
                    updated_count += 1
                    break
        
        self.stdout.write(
            self.style.SUCCESS(
                f'成功為 {updated_count} 張票券生成 ticket_code'
            )
        )