import logging
from typing import Optional, Sequence

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_s3.client import S3Client
from mypy_boto3_s3.type_defs import (
    CompletedMultipartUploadTypeDef,
    CompletedPartTypeDef,
    PartTypeDef,
)

from ..core.config import settings

log = logging.getLogger(__name__)


class S3Adapter:
    def __init__(self):
        self._client: S3Client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        self.bucket: str = settings.s3_bucket

    async def initiate(self, key: str, content_type: str) -> Optional[str]:
        try:
            resp = self._client.create_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
            return resp["UploadId"]
        except ClientError:
            log.exception("initiate multipart failed")
            return None

    async def presign(self, key: str, upload_id: str, part: int) -> Optional[str]:
        try:
            return self._client.generate_presigned_url(
                "upload_part",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "UploadId": upload_id,
                    "PartNumber": part,
                },
                ExpiresIn=3600,
            )
        except ClientError:
            log.exception("presign failed")
            return None

    async def list_parts(self, key: str, upload_id: str) -> list[PartTypeDef]:
        resp = self._client.list_parts(Bucket=self.bucket, Key=key, UploadId=upload_id)
        return resp.get("Parts", [])

    async def complete(self, key: str, upload_id: str, parts: Sequence[CompletedPartTypeDef]) -> bool:
        try:
            multipart: CompletedMultipartUploadTypeDef = {"Parts": parts}
            self._client.complete_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload=multipart,
            )
            return True
        except ClientError:
            log.exception("complete multipart failed")
            return False
