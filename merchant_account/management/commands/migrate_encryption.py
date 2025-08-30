import base64
import os
from django.core.management.base import BaseCommand
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet
from merchant_account.models import Merchant


class Command(BaseCommand):
    help = '遷移現存商家資料的加密方式（從舊的不安全方式遷移到新的安全方式）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅顯示將要處理的資料，不實際修改'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制執行遷移，即使檢測到風險'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.force = options['force']

        self.stdout.write('開始檢查加密金鑰配置...')
        
        # 檢查新的加密金鑰是否已設定
        try:
            new_key = os.getenv('PAYMENT_ENCRYPTION_KEY')
            if not new_key:
                raise ImproperlyConfigured("PAYMENT_ENCRYPTION_KEY 未設定")
            # 驗證新金鑰格式
            Fernet(new_key.encode())
            self.stdout.write(self.style.SUCCESS('✓ 新的加密金鑰格式正確'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 新的加密金鑰配置錯誤: {e}')
            )
            self.stdout.write('請先使用 "python manage.py generate_payment_key" 產生並設定新金鑰')
            return

        # 檢查是否有需要遷移的資料
        merchants = Merchant.objects.all()
        if not merchants.exists():
            self.stdout.write('沒有需要遷移的商家資料')
            return

        self.stdout.write(f'發現 {merchants.count()} 個商家記錄需要檢查')

        # 檢查哪些記錄可能使用舊加密方式
        fields_to_migrate = [
            'newebpay_merchant_id', 'newebpay_hash_key', 'newebpay_hash_iv',
            'linepay_channel_id', 'linepay_channel_secret'
        ]

        migration_needed = []
        for merchant in merchants:
            merchant_data = {}
            has_encrypted_data = False
            
            for field_name in fields_to_migrate:
                field_value = getattr(merchant, field_name, '')
                if field_value:
                    # 嘗試檢測這是否為舊格式加密的資料
                    if self._is_old_encrypted_data(field_value):
                        merchant_data[field_name] = field_value
                        has_encrypted_data = True

            if has_encrypted_data:
                migration_needed.append((merchant, merchant_data))

        if not migration_needed:
            self.stdout.write(self.style.SUCCESS('沒有發現使用舊加密方式的資料'))
            return

        self.stdout.write(
            self.style.WARNING(f'發現 {len(migration_needed)} 個商家有使用舊加密方式的資料需要遷移')
        )

        if self.dry_run:
            self.stdout.write('\n=== DRY RUN 模式 - 僅顯示將要處理的資料 ===')
            for merchant, data in migration_needed:
                self.stdout.write(f'\n商家 ID {merchant.id}:')
                for field_name, encrypted_value in data.items():
                    decrypted = self._decrypt_with_old_method(encrypted_value)
                    self.stdout.write(f'  {field_name}: {decrypted[:20]}... (舊加密)')
            self.stdout.write('\n使用 --force 參數執行實際遷移')
            return

        # 執行實際遷移
        if not self.force:
            confirm = input('這將修改商家的敏感資料。確定要繼續嗎？ (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('遷移已取消')
                return

        self.stdout.write('\n開始執行遷移...')
        success_count = 0
        error_count = 0

        for merchant, old_data in migration_needed:
            try:
                # 解密舊資料並用新方式重新加密
                for field_name, old_encrypted_value in old_data.items():
                    decrypted_value = self._decrypt_with_old_method(old_encrypted_value)
                    new_encrypted_value = merchant._encrypt_data(decrypted_value)
                    setattr(merchant, field_name, new_encrypted_value)

                merchant.save()
                success_count += 1
                self.stdout.write(f'✓ 商家 ID {merchant.id} 遷移成功')

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'❌ 商家 ID {merchant.id} 遷移失敗: {e}')
                )

        self.stdout.write(
            f'\n遷移完成: {success_count} 成功, {error_count} 失敗'
        )

    def _is_old_encrypted_data(self, data):
        """檢測資料是否為舊格式加密"""
        if not data or len(data) < 50:
            return False
        try:
            # 嘗試用舊方式解密，如果成功可能就是舊格式
            self._decrypt_with_old_method(data)
            return True
        except:
            return False

    def _decrypt_with_old_method(self, encrypted_data):
        """使用舊的加密方法解密資料"""
        if not encrypted_data:
            return ''
        
        # 舊的金鑰生成方式
        key = os.getenv('PAYMENT_ENCRYPTION_KEY', 'dev-key-32chars-for-testing-only!')
        if isinstance(key, str):
            key = key.encode()
        old_key = base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))
        
        fernet = Fernet(old_key)
        decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
        return fernet.decrypt(decoded_data).decode()