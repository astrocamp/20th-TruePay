"""
票券相關的自定義例外類別
"""

class TicketError(Exception):
    """票券相關錯誤的基礎類別"""
    pass

class TicketValidationError(TicketError):
    """票券驗證錯誤"""
    pass

class TicketUsageError(TicketError):
    """票券使用錯誤"""
    pass

class TicketNotFoundError(TicketError):
    """票券不存在"""
    pass