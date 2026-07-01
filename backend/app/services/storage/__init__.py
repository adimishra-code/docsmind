from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_storage_backend():
    provider = settings.STORAGE_PROVIDER.lower().strip()
    if provider == "s3":
        from app.services.storage.s3 import S3StorageAdapter
        logger.info("Using S3 storage backend", bucket=settings.S3_BUCKET_NAME)
        return S3StorageAdapter()
    logger.info("Using local storage backend", path="storage")
    from app.services.storage.local import LocalStorage
    return LocalStorage()
