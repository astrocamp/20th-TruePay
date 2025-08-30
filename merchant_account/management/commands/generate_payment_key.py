from django.core.management.base import BaseCommand
from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = '產生用於加密商家敏感資料的安全金鑰'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-instructions',
            action='store_true',
            help='顯示如何設定環境變數的詳細說明'
        )

    def handle(self, *args, **options):
        # 產生一個新的安全金鑰
        key = Fernet.generate_key()
        key_str = key.decode()
        
        self.stdout.write(
            self.style.SUCCESS('✓ 已成功產生安全的加密金鑰')
        )
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.WARNING('重要：請妥善保存以下金鑰'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'\n{key_str}\n')
        self.stdout.write('=' * 60)
        
        if options['show_instructions']:
            self.show_setup_instructions(key_str)
        else:
            self.stdout.write('\n使用 --show-instructions 參數查看詳細設定說明')
    
    def show_setup_instructions(self, key_str):
        self.stdout.write('\n' + self.style.SUCCESS('環境變數設定說明：'))
        
        self.stdout.write('\n1. 在 .env 檔案中加入（開發環境）：')
        self.stdout.write(f'   PAYMENT_ENCRYPTION_KEY={key_str}')
        
        self.stdout.write('\n2. 在生產環境中設定：')
        self.stdout.write(f'   export PAYMENT_ENCRYPTION_KEY="{key_str}"')
        
        self.stdout.write('\n3. 如使用 Docker，在 docker-compose.yml 中：')
        self.stdout.write('   environment:')
        self.stdout.write(f'     - PAYMENT_ENCRYPTION_KEY={key_str}')
        
        self.stdout.write('\n' + self.style.WARNING('安全提醒：'))
        self.stdout.write('• 此金鑰用於加密商家的敏感資料（API 金鑰、密鑰等）')
        self.stdout.write('• 請勿將此金鑰提交到版本控制系統中')
        self.stdout.write('• 如果遺失此金鑰，已加密的資料將無法解密')
        self.stdout.write('• 建議定期備份此金鑰到安全的地方')
        
        self.stdout.write('\n' + self.style.SUCCESS('設定完成後，重新啟動應用程式即可生效。'))