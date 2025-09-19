"""
QR Code 工具模組
提供統一的 QR Code 生成功能，支援添加 logo
"""

import qrcode
from PIL import Image, ImageDraw
from io import BytesIO
import base64
from django.conf import settings
import os


def generate_qr_code_with_logo(data, logo_path=None, logo_size_ratio=0.25, error_correction=qrcode.constants.ERROR_CORRECT_M):
    """
    生成帶有 logo 的 QR Code

    Args:
        data (str): QR Code 要編碼的資料
        logo_path (str): Logo 圖片的路徑，如果為 None 則使用預設的 favicon
        logo_size_ratio (float): Logo 相對於 QR Code 的大小比例 (0.1-0.3 推薦)
        error_correction: QR Code 的錯誤修正等級

    Returns:
        str: base64 編碼的 PNG 圖片
    """

    # 如果沒有指定 logo 路徑，使用預設的 favicon
    if logo_path is None:
        logo_path = os.path.join(settings.BASE_DIR, 'src', 'favicon.ico')

    # 創建 QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=error_correction,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # 生成 QR Code 圖片
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')

    # 嘗試添加 logo
    try:
        if os.path.exists(logo_path):
            # 載入 logo
            logo = Image.open(logo_path)

            # 轉換為 RGBA 模式
            logo = logo.convert('RGBA')

            # 計算 logo 尺寸
            qr_width, qr_height = qr_img.size
            logo_size = int(min(qr_width, qr_height) * logo_size_ratio)

            # 調整 logo 大小
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

            # 創建圓形白色背景
            background_size = logo_size
            background = Image.new('RGBA', (background_size, background_size), (255, 255, 255, 255))

            # 創建圓形遮罩
            mask = Image.new('L', (background_size, background_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse([0, 0, background_size, background_size], fill=255)

            # 應用圓形遮罩到白色背景
            background.putalpha(mask)

            # 調整 logo 大小（留一些邊距）
            logo_margin = logo_size // 4
            inner_size = logo_size - logo_margin * 2
            logo_resized = logo.resize((inner_size, inner_size), Image.Resampling.LANCZOS)

            # 創建最終的 logo（白色圓形背景 + logo）
            final_logo = background.copy()
            logo_pos = ((background_size - inner_size) // 2, (background_size - inner_size) // 2)
            final_logo.paste(logo_resized, logo_pos, logo_resized)

            # 計算 logo 在 QR Code 中的位置（居中）
            logo_x = (qr_width - logo_size) // 2
            logo_y = (qr_height - logo_size) // 2

            # 將 logo 粘貼到 QR Code 上
            qr_img.paste(final_logo, (logo_x, logo_y), final_logo)

    except Exception as e:
        # 如果添加 logo 失敗，就使用原始的 QR Code
        print(f"Warning: Could not add logo to QR code: {e}")

    # 轉換為 base64
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode()


def generate_simple_qr_code(data, **kwargs):
    """
    生成簡單的 QR Code（不帶 logo）

    Args:
        data (str): QR Code 要編碼的資料
        **kwargs: 其他 QR Code 參數

    Returns:
        str: base64 編碼的 PNG 圖片
    """

    # 提取參數
    version = kwargs.get('version', 1)
    error_correction = kwargs.get('error_correction', qrcode.constants.ERROR_CORRECT_M)
    box_size = kwargs.get('box_size', 10)
    border = kwargs.get('border', 4)
    fill_color = kwargs.get('fill_color', "black")
    back_color = kwargs.get('back_color', "white")

    # 創建 QR Code
    qr = qrcode.QRCode(
        version=version,
        error_correction=error_correction,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # 生成圖片
    img = qr.make_image(fill_color=fill_color, back_color=back_color)

    # 轉換為 base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode()