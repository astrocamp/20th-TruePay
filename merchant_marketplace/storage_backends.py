from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class MediaStorage(S3Boto3Storage):
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    region_name = settings.AWS_S3_REGION_NAME
    file_overwrite = False
    default_acl = 'public-read'  # 使用 ACL 設為公開讀取
    querystring_auth = False
    object_parameters = {
        'CacheControl': 'max-age=86400',
    }