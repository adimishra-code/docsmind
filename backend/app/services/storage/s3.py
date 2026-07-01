from __future__ import annotations

import pathlib
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.services.storage.base import StorageInterface

logger = get_logger(__name__)


class S3StorageAdapter(StorageInterface):
    """S3-compatible cloud storage adapter using aioboto3."""

    def __init__(self) -> None:
        self.bucket = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.session = aioboto3.Session(
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=self.region,
        )

    async def _ensure_bucket_exists(self) -> None:
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket)
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "404":
                    logger.info("Creating S3 bucket", bucket=self.bucket)
                    kwargs: dict[str, Any] = {"Bucket": self.bucket}
                    if self.region != "us-east-1":
                        kwargs["CreateBucketConfiguration"] = {
                            "LocationConstraint": self.region,
                        }
                    await s3.create_bucket(**kwargs)
                else:
                    raise

    async def upload(self, file_content: bytes, destination_path: str) -> str:
        sanitized = destination_path.replace("\\", "/")
        logger.info("Uploading to S3", bucket=self.bucket, key=sanitized)
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            await s3.put_object(Bucket=self.bucket, Key=sanitized, Body=file_content)
        return sanitized

    async def download(self, storage_path: str) -> bytes:
        key = storage_path.replace("\\", "/")
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            try:
                obj = await s3.get_object(Bucket=self.bucket, Key=key)
                return await obj["Body"].read()
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "NoSuchKey":
                    raise NotFoundError("Stored file not found in S3.")
                raise

    async def delete(self, storage_path: str) -> None:
        key = storage_path.replace("\\", "/")
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=key)
            except ClientError:
                logger.warning("S3 delete failed — object may not exist", key=key)
