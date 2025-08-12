# app/services/storage_service.py
from __future__ import annotations
import os
from typing import Optional
import boto3
from botocore.client import Config

class S3StorageService:
    """
    Thin wrapper around boto3 S3 for MinIO/any S3-compatible storage.
    """
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        use_ssl: Optional[bool] = None,
        force_path_style: Optional[bool] = None,
    ) -> None:
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT", "http://minio:9000")
        self.region_name = region_name or os.getenv("S3_REGION", "us-east-1")
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("S3_SECRET_KEY", "minioadmin")
        self.bucket = bucket_name or os.getenv("S3_BUCKET", "profile-pics")
        self.use_ssl = (str(use_ssl).lower() if use_ssl is not None else os.getenv("S3_USE_SSL", "false")).lower() == "true"
        self.force_path_style = (str(force_path_style).lower() if force_path_style is not None else os.getenv("S3_FORCE_PATH_STYLE", "true")).lower() == "true"

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=self.use_ssl,
            config=Config(s3={"addressing_style": "path" if self.force_path_style else "auto"}),
        )
        self._ensure_bucket()

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, ACL="public-read"
        )
        return self.object_url(key)

    def upload_file(self, key: str, file_path: str, content_type: Optional[str] = None) -> str:
        extra = {"ACL": "public-read"}
        if content_type:
            extra["ContentType"] = content_type
        self.client.upload_file(file_path, self.bucket, key, ExtraArgs=extra)
        return self.object_url(key)

    def object_url(self, key: str) -> str:
        return f"{self.endpoint_url.rstrip('/')}/{self.bucket}/{key}"

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                kwargs = {"Bucket": self.bucket}
                if self.region_name and self.region_name != "us-east-1":
                    kwargs["CreateBucketConfiguration"] = {"LocationConstraint": self.region_name}
                self.client.create_bucket(**kwargs)
            except Exception:
                pass
