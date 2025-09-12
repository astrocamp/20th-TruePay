"""
TruePay Payments Celery Tasks
票券相關的 Celery 異步任務
"""

import logging
from celery import shared_task
from django.utils import timezone
from .models import OrderItem

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='payments.check_ticket_expiry')
def check_ticket_expiry(self):
    """
    檢查票券到期狀況並發送通知
    每分鐘執行一次，檢查是否有票券需要發送到期通知
    
    Returns:
        dict: 執行結果統計
    """
    try:
        logger.info("開始執行票券到期檢查任務")
        start_time = timezone.now()
        
        # 呼叫 OrderItem 的批量通知方法
        result = OrderItem.send_all_expiry_notifications()
        
        end_time = timezone.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 記錄執行結果
        logger.info(
            f"票券到期檢查任務完成 - "
            f"檢查數量: {result['total_checked']}, "
            f"通知發送: {result['notifications_sent']}, "
            f"錯誤數量: {result['errors_count']}, "
            f"成功率: {result['success_rate']:.2f}%, "
            f"執行時間: {execution_time:.2f}秒"
        )
        
        # 如果有錯誤，記錄警告
        if result['errors_count'] > 0:
            logger.warning(f"票券通知發送過程中發生 {result['errors_count']} 個錯誤")
        
        # 回傳詳細結果供監控使用
        return {
            'task_name': 'check_ticket_expiry',
            'execution_time': execution_time,
            'timestamp': end_time.isoformat(),
            **result
        }
        
    except Exception as e:
        logger.error(f"票券到期檢查任務執行失敗: {str(e)}")
        # 重新拋出異常，讓 Celery 知道任務失敗
        raise self.retry(exc=e, countdown=60, max_retries=3)


@shared_task(bind=True, name='payments.cleanup_expired_tickets')
def cleanup_expired_tickets(self):
    """
    清理過期票券狀態
    每小時執行一次，將已過期但狀態仍為 'unused' 的票券更新為 'expired'
    
    Returns:
        dict: 清理結果統計
    """
    try:
        logger.info("開始執行過期票券狀態清理任務")
        start_time = timezone.now()
        
        # 查找已過期但狀態仍為 'unused' 的票券
        expired_tickets = OrderItem.objects.filter(
            status='unused',
            valid_until__lt=timezone.now(),
            order__status='paid'
        )
        
        # 統計數量
        total_expired = expired_tickets.count()
        
        # 批量更新狀態為 'expired'
        updated_count = expired_tickets.update(status='expired')
        
        end_time = timezone.now()
        execution_time = (end_time - start_time).total_seconds()
        
        logger.info(
            f"過期票券清理任務完成 - "
            f"發現過期票券: {total_expired}, "
            f"更新數量: {updated_count}, "
            f"執行時間: {execution_time:.2f}秒"
        )
        
        return {
            'task_name': 'cleanup_expired_tickets',
            'execution_time': execution_time,
            'timestamp': end_time.isoformat(),
            'total_expired': total_expired,
            'updated_count': updated_count
        }
        
    except Exception as e:
        logger.error(f"過期票券清理任務執行失敗: {str(e)}")
        raise self.retry(exc=e, countdown=300, max_retries=3)


@shared_task(name='payments.send_daily_ticket_report')
def send_daily_ticket_report():
    """
    發送每日票券統計報表
    每日 23:00 執行，統計當日的票券使用情況
    
    Returns:
        dict: 統計結果
    """
    try:
        logger.info("開始生成每日票券統計報表")
        
        today = timezone.now().date()
        
        # 統計今日數據
        today_stats = {
            'created': OrderItem.objects.filter(created_at__date=today).count(),
            'used': OrderItem.objects.filter(used_at__date=today).count(),
            'expired_today': OrderItem.objects.filter(
                status='expired',
                valid_until__date=today
            ).count(),
            'notifications_sent': OrderItem.objects.filter(
                expiry_notification_sent__date=today
            ).count(),
        }
        
        # 整體統計
        overall_stats = {
            'total_active': OrderItem.objects.filter(status='unused').count(),
            'total_used': OrderItem.objects.filter(status='used').count(),
            'total_expired': OrderItem.objects.filter(status='expired').count(),
        }
        
        logger.info(
            f"每日票券統計 - "
            f"今日新增: {today_stats['created']}, "
            f"今日使用: {today_stats['used']}, "
            f"今日過期: {today_stats['expired_today']}, "
            f"通知發送: {today_stats['notifications_sent']}"
        )
        
        return {
            'task_name': 'send_daily_ticket_report',
            'report_date': today.isoformat(),
            'today_stats': today_stats,
            'overall_stats': overall_stats
        }
        
    except Exception as e:
        logger.error(f"每日票券統計報表生成失敗: {str(e)}")
        return {'error': str(e)}