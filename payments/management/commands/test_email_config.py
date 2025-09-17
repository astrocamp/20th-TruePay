"""
測試郵件配置命令
用於驗證郵件服務提供商設定是否正確
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
import os


class Command(BaseCommand):
    help = '測試郵件配置設定'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-test',
            action='store_true',
            help='發送測試郵件',
        )
        parser.add_argument(
            '--to',
            type=str,
            default='test@example.com',
            help='測試郵件收件人',
        )

    def handle(self, *args, **options):
        """執行命令"""
        self.stdout.write('=' * 50)
        self.stdout.write(self.style.SUCCESS('郵件配置檢查'))
        self.stdout.write('=' * 50)
        
        # 顯示目前配置
        email_provider = getattr(settings, 'EMAIL_PROVIDER', 'unknown')
        self.stdout.write(f'郵件服務提供商: {email_provider}')
        self.stdout.write(f'郵件主機: {settings.EMAIL_HOST}')
        self.stdout.write(f'埠號: {settings.EMAIL_PORT}')
        self.stdout.write(f'TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'SSL: {settings.EMAIL_USE_SSL}')
        self.stdout.write(f'用戶名: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'密碼已設定: {"是" if settings.EMAIL_HOST_PASSWORD else "否"}')
        self.stdout.write(f'發送地址: {settings.DEFAULT_FROM_EMAIL}')
        
        # 檢查環境變數
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('環境變數檢查')
        self.stdout.write('=' * 50)
        
        email_provider_env = os.getenv('EMAIL_PROVIDER', 'Not set')
        self.stdout.write(f'EMAIL_PROVIDER: {email_provider_env}')
        
        if email_provider == 'mailtrap':
            mailtrap_user = os.getenv('MAILTRAP_USERNAME', 'Not set')
            mailtrap_pass = bool(os.getenv('MAILTRAP_PASSWORD'))
            self.stdout.write(f'MAILTRAP_USERNAME: {mailtrap_user}')
            self.stdout.write(f'MAILTRAP_PASSWORD: {"已設定" if mailtrap_pass else "未設定"}')
        elif email_provider == 'resend':
            resend_key = bool(os.getenv('RESEND_API_KEY'))
            self.stdout.write(f'RESEND_API_KEY: {"已設定" if resend_key else "未設定"}')
        
        # 發送測試郵件
        if options['send_test']:
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write('發送測試郵件')
            self.stdout.write('=' * 50)
            
            to_email = options['to']
            self.stdout.write(f'收件人: {to_email}')
            
            try:
                send_mail(
                    subject='TruePay 郵件配置測試',
                    message='這是一封測試郵件，用於驗證 TruePay 的郵件配置是否正常工作。',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[to_email],
                    html_message='''
                    <h2>TruePay 郵件配置測試</h2>
                    <p>恭喜！您的郵件配置已正常工作。</p>
                    <p><strong>郵件服務提供商:</strong> {}</p>
                    <p><strong>測試時間:</strong> {}</p>
                    <hr>
                    <p><em>此郵件由 TruePay 系統自動發送</em></p>
                    '''.format(email_provider, '2025-09-12 05:51:53'),
                    fail_silently=False,
                )
                self.stdout.write(
                    self.style.SUCCESS('測試郵件發送成功！')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'測試郵件發送失敗: {str(e)}')
                )
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('使用提示')
        self.stdout.write('=' * 50)
        self.stdout.write('切換到 Mailtrap:')
        self.stdout.write('  1. 在 .env 中設定: EMAIL_PROVIDER=mailtrap')
        self.stdout.write('  2. 設定 MAILTRAP_USERNAME 和 MAILTRAP_PASSWORD')
        self.stdout.write('')
        self.stdout.write('切換到 Resend:')
        self.stdout.write('  1. 在 .env 中設定: EMAIL_PROVIDER=resend')
        self.stdout.write('  2. 設定 RESEND_API_KEY')
        self.stdout.write('')
        self.stdout.write('測試發送: python manage.py test_email_config --send-test --to=your@email.com')