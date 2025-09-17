import os
from django.core.exceptions import ValidationError
from django.conf import settings
from PIL import Image


def validate_image_file(file):
    """
    驗證上傳的檔案是否為有效的圖片檔案
    """
    # 檢查檔案大小
    max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024)  # 預設 5MB
    if file.size > max_size:
        raise ValidationError(f'檔案大小不能超過 {max_size // (1024 * 1024)}MB')

    # 檢查檔案副檔名
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    file_extension = os.path.splitext(file.name)[1].lower()
    if file_extension not in valid_extensions:
        raise ValidationError(f'不支援的檔案格式。支援格式：{", ".join(valid_extensions)}')

    # 使用 PIL 驗證圖片
    try:
        file.seek(0)
        with Image.open(file) as img:
            img.verify()  # 驗證圖片是否有效

        # 重新開啟圖片檢查尺寸（verify() 後無法再讀取）
        file.seek(0)
        with Image.open(file) as img:
            width, height = img.size
            max_dimension = 4096  # 最大尺寸 4096px
            if width > max_dimension or height > max_dimension:
                raise ValidationError(f'圖片尺寸過大，寬度和高度都不能超過 {max_dimension}px')

            # 檢查最小尺寸
            min_dimension = 100  # 最小尺寸 100px
            if width < min_dimension or height < min_dimension:
                raise ValidationError(f'圖片尺寸過小，寬度和高度都不能小於 {min_dimension}px')

    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f'無效的圖片檔案：{str(e)}')
    finally:
        file.seek(0)  # 重置檔案指針


def validate_required_image(file):
    """
    驗證圖片是否為必填
    """
    if not file:
        raise ValidationError('商品圖片為必填項目，請上傳圖片')

    # 呼叫基本圖片驗證
    validate_image_file(file)