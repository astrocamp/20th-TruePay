import os
from django.core.exceptions import ValidationError
from django.conf import settings
from PIL import Image
import magic


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

    # 檢查檔案 MIME 類型
    try:
        # 重置檔案指針到開頭
        file.seek(0)
        # 讀取檔案頭部用於檢測
        file_content = file.read(1024)
        file.seek(0)  # 重置指針

        # 使用 python-magic 檢測真實檔案類型
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            valid_mime_types = [
                'image/jpeg',
                'image/jpg',
                'image/png',
                'image/gif',
                'image/webp'
            ]
            if mime_type not in valid_mime_types:
                raise ValidationError('檔案內容不是有效的圖片格式')
        except:
            # 如果 python-magic 不可用，使用 PIL 作為備選
            pass
    except Exception:
        raise ValidationError('無法讀取檔案，請確認檔案沒有損壞')

    # 使用 PIL 驗證圖片
    try:
        file.seek(0)
        with Image.open(file) as img:
            img.verify()  # 驗證圖片是否有效

            # 檢查圖片尺寸
            if hasattr(img, 'size'):
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