import logging
from typing import Optional, Sequence

import aioboto3
from botocore.exceptions import ClientError
from mypy_boto3_s3.type_defs import (
    CompletedMultipartUploadTypeDef,
    CompletedPartTypeDef,
    PartTypeDef,
)

from ..core.config import settings

log = logging.getLogger(__name__)


class S3Adapter:
    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        self.bucket: str = settings.s3_bucket

    async def initiate(self, key: str, content_type: str) -> Optional[str]:
        """Initiate multipart upload"""
        try:
            async with self.session.client('s3') as client:
                response = await client.create_multipart_upload(
                    Bucket=self.bucket,
                    Key=key,
                    ContentType=content_type,
                    ServerSideEncryption="AES256",
                )
                return response["UploadId"]
        except ClientError as e:
            log.error(f"Failed to initiate multipart upload for {key}: {str(e)}")
            return None

    async def presign(self, key: str, upload_id: str, part: int) -> Optional[str]:
        """Generate presigned URL for chunk upload"""
        try:
            async with self.session.client('s3') as client:
                return await client.generate_presigned_url(
                    "upload_part",
                    Params={
                        "Bucket": self.bucket,
                        "Key": key,
                        "UploadId": upload_id,
                        "PartNumber": part,
                    },
                    ExpiresIn=3600,
                )
        except ClientError as e:
            log.error(f"Failed to generate presigned URL for {key} part {part}: {str(e)}")
            return None

    async def list_parts(self, key: str, upload_id: str) -> list[PartTypeDef]:
        """List uploaded parts for multipart upload"""
        try:
            async with self.session.client('s3') as client:
                response = await client.list_parts(
                    Bucket=self.bucket, 
                    Key=key, 
                    UploadId=upload_id
                )
                return response.get("Parts", [])
        except ClientError as e:
            log.error(f"Failed to list parts for {key}: {str(e)}")
            return []

    async def complete(self, key: str, upload_id: str, parts: Sequence[CompletedPartTypeDef]) -> bool:
        """Complete multipart upload"""
        try:
            async with self.session.client('s3') as client:
                multipart: CompletedMultipartUploadTypeDef = {"Parts": parts}
                await client.complete_multipart_upload(
                    Bucket=self.bucket,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload=multipart,
                )
                return True
        except ClientError as e:
            log.error(f"Failed to complete multipart upload for {key}: {str(e)}")
            return False
