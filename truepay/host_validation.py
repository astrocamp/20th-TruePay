"""
自訂域名驗證函數
用於 django-dynamic-host 套件
"""
import logging

logger = logging.getLogger(__name__)


def validate_host(host, request):
    """
    驗證主機是否被允許訪問
    
    Args:
        host (str): 請求的主機名 (例如: ushionagisa.work)
        request: Django request 物件
    
    Returns:
        bool: True 如果主機被允許，否則 False
    """
    
    # 1. 檢查基本允許的主機
    base_hosts = [
        '127.0.0.1',
        'localhost',
        'truepay.tw',
        '54.95.179.51',  # EC2 IP
    ]
    
    if host in base_hosts:
        logger.info(f"Host '{host}' allowed - base host")
        return True
    
    # 2. 檢查 .truepay.tw 子域名
    if host.endswith('.truepay.tw') or host == 'truepay.tw':
        logger.info(f"Host '{host}' allowed - truepay subdomain")
        return True
    
    # 3. 檢查商家自訂域名
    try:
        from merchant_account.models import MerchantOwnDomain
        
        # 檢查資料庫中的活躍自訂域名
        is_custom_domain = MerchantOwnDomain.objects.filter(
            domain_name=host,
            is_active=True
        ).exists()
        
        if is_custom_domain:
            logger.info(f"Host '{host}' allowed - custom merchant domain")
            return True
        
    except Exception as e:
        # 資料庫未準備好時的備援處理
        logger.warning(f"Database error while checking host '{host}': {e}")
        
        # 如果是開發環境，允許通過
        import os
        if os.getenv('DEBUG', 'False').lower() == 'true':
            logger.info(f"Host '{host}' allowed - debug mode fallback")
            return True
    
    # 4. 開發環境的額外檢查
    dev_patterns = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
    ]
    
    for pattern in dev_patterns:
        if host.startswith(pattern):
            logger.info(f"Host '{host}' allowed - development pattern")
            return True
    
    logger.warning(f"Host '{host}' rejected - no matching rule")
    return False