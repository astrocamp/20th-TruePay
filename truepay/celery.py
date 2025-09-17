"""
TruePay Celery Configuration
配置 Celery 應用程式和任務佇列系統
"""

import os
from celery import Celery
from django.conf import settings

# 設定 Django settings 模組
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'truepay.settings')

# 創建 Celery 應用程式
app = Celery('truepay')

# 從 Django settings 載入配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自動發現所有 Django app 中的任務
app.autodiscover_tasks()

# 除錯用的任務
@app.task(bind=True)
def debug_task(self):
    """除錯任務，用於測試 Celery 是否正常運作"""
    print(f'Request: {self.request!r}')