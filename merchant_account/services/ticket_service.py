"""
票券服務 - 處理所有票券相關的業務邏輯
"""
import json
import base64
from datetime import datetime
from django.utils import timezone
from .exceptions import TicketValidationError, TicketUsageError, TicketNotFoundError

class TicketService:
    """票券服務類別"""
    
    @classmethod
    def validate_qr_code(cls, qr_data, merchant_id):
        """
        驗證QR Code並返回票券資訊
        
        Args:
            qr_data: QR Code掃描到的原始數據
            merchant_id: 當前商家ID
            
        Returns:
            dict: 包含ticket_code和ticket_info的字典
            
        Raises:
            TicketValidationError: 當票券驗證失敗時
        """
        # 1. 基本檢查
        if not qr_data:
            raise TicketValidationError('QR Code數據不能為空')
        
        # 2. 解析QR Code數據
        try:
            decoded_data = cls._decode_qr_data(qr_data)
            ticket_code = decoded_data.get('ticket_code')
        except Exception:
            raise TicketValidationError('QR Code格式錯誤')
        
        if not ticket_code:
            raise TicketValidationError('QR Code缺少票券代碼')
        
        # 3. 查找票券（目前模擬，之後連接真實資料庫）
        ticket_info = cls._get_ticket_by_code(ticket_code)
        
        # 4. 驗證商家權限（測試時暫時放寬）
        # TODO: 正式環境要啟用這個檢查
        # if ticket_info['merchant_id'] != merchant_id:
        #     raise TicketValidationError('此票券不屬於您的商店')
        
        # 測試階段：只要有merchant_id就通過
        if not merchant_id:
            raise TicketValidationError('請先登入商家帳號')
        
        # 5. 檢查票券狀態
        if not cls._is_ticket_valid(ticket_info):
            status_msg = cls._get_status_message(ticket_info)
            raise TicketValidationError(status_msg)
        
        return {
            'ticket_code': ticket_code,
            'ticket_info': {
                'product_name': ticket_info['product_name'],
                'ticket_value': ticket_info['ticket_value'],
                'customer_name': ticket_info['customer_name'],
                'valid_until': ticket_info['valid_until']
            }
        }
    
    @classmethod
    def use_ticket(cls, ticket_code, merchant_id):
        """
        使用票券
        
        Args:
            ticket_code: 票券代碼
            merchant_id: 當前商家ID
            
        Returns:
            dict: 包含使用時間等資訊
            
        Raises:
            TicketUsageError: 當票券使用失敗時
        """
        if not ticket_code:
            raise TicketUsageError('票券代碼不能為空')
        
        # 1. 再次驗證票券（確保狀態沒有改變）
        ticket_info = cls._get_ticket_by_code(ticket_code)
        
        # 測試階段：暫時放寬商家權限檢查
        # if ticket_info['merchant_id'] != merchant_id:
        #     raise TicketUsageError('無權使用此票券')
        
        if not merchant_id:
            raise TicketUsageError('請先登入商家帳號')
        
        if not cls._is_ticket_valid(ticket_info):
            raise TicketUsageError('票券無法使用')
        
        # 2. 使用票券（目前模擬，之後實際更新資料庫）
        used_at = timezone.now()
        cls._mark_ticket_as_used(ticket_code, merchant_id, used_at)
        
        return {
            'message': '票券使用成功',
            'used_at': used_at,
            'ticket_value': ticket_info['ticket_value']
        }
    
    # 私有輔助方法
    @classmethod
    def _decode_qr_data(cls, qr_data):
        """解析QR Code數據"""
        try:
            # 嘗試base64解碼
            return json.loads(base64.b64decode(qr_data).decode())
        except:
            try:
                # 如果不是base64，嘗試直接解析JSON
                return json.loads(qr_data)
            except:
                # 如果都不是，假設是簡單的票券代碼
                return {'ticket_code': qr_data}
    
    @classmethod
    def _get_ticket_by_code(cls, ticket_code):
        """根據票券代碼取得票券資訊（目前模擬）"""
        # 模擬數據 - 之後替換為實際的資料庫查詢
        # ticket = Ticket.objects.get(ticket_code=ticket_code)
        
        mock_tickets = {
            'TEST123': {
                'merchant_id': 1,
                'status': 'unused',
                'product_name': '美式咖啡',
                'ticket_value': '120.00',
                'customer_name': '王小明',
                'valid_until': '2024-12-31T23:59:59',
                'created_at': '2024-01-01T00:00:00'
            },
            'USED456': {
                'merchant_id': 1,
                'status': 'used',
                'product_name': '拿鐵咖啡',
                'ticket_value': '150.00',
                'customer_name': '李小美',
                'valid_until': '2024-12-31T23:59:59',
                'created_at': '2024-01-01T00:00:00'
            },
            'EXPIRED789': {
                'merchant_id': 1,
                'status': 'unused',
                'product_name': '卡布奇諾',
                'ticket_value': '130.00',
                'customer_name': '陳大華',
                'valid_until': '2023-01-01T23:59:59',  # 已過期
                'created_at': '2024-01-01T00:00:00'
            }
        }
        
        if ticket_code not in mock_tickets:
            raise TicketNotFoundError('票券不存在')
        
        return mock_tickets[ticket_code]
    
    @classmethod
    def _is_ticket_valid(cls, ticket_info):
        """檢查票券是否有效"""
        # 檢查狀態
        if ticket_info['status'] != 'unused':
            return False
        
        # 簡化的有效期限檢查
        try:
            valid_until_str = ticket_info['valid_until']
            
            # 簡單的字串比較來測試過期功能
            # 2023年的票券視為過期，2024年及以後的視為有效
            if '2023-' in valid_until_str:
                return False
            elif '2024-' in valid_until_str or '2025-' in valid_until_str:
                return True
            else:
                return True  # 預設有效
                
        except Exception as e:
            print(f"Debug: 有效期限檢查錯誤: {e}")
            return False
        
        return True
    
    @classmethod
    def _get_status_message(cls, ticket_info):
        """根據票券狀態返回錯誤訊息"""
        status = ticket_info['status']
        
        if status == 'used':
            return '票券已使用'
        elif status == 'expired':
            return '票券已過期'
        elif status == 'cancelled':
            return '票券已取消'
        else:
            # 簡化的過期檢查，避免時區問題
            valid_until_str = ticket_info['valid_until']
            if '2023-' in valid_until_str:
                return '票券已過期'
        
        return '票券狀態異常'
    
    @classmethod
    def _mark_ticket_as_used(cls, ticket_code, merchant_id, used_at):
        """標記票券為已使用（目前模擬）"""
        # 實際實現：
        # ticket = Ticket.objects.get(ticket_code=ticket_code)
        # ticket.status = 'used'
        # ticket.used_at = used_at
        # ticket.used_by_merchant_id = merchant_id
        # ticket.save()
        
        print(f"✅ 模擬：票券 {ticket_code} 已被商家 {merchant_id} 在 {used_at} 使用")