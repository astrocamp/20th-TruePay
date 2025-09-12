# Ensure Celery app is loaded when Django starts
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not available, skip for now
    pass