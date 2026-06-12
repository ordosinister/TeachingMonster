"""Cloud storage integration for uploading generated videos to AWS S3.

Uses boto3 with Signature V4 signing and generates presigned URLs
for secure, time-limited download access.
"""

import os
import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger("Storage")



class CloudStorage:
    """Manages upload of generated videos to AWS S3.

    Handles S3 upload with SigV4 signing and generates presigned
    download URLs (default 48-hour expiry).

    Attributes:
        region: AWS region for the S3 bucket.
        bucket_name: Target S3 bucket name.
        s3: boto3 S3 client instance.
    """
    def __init__(self):
        # We MUST specify the region for newer S3 buckets (e.g., eu-central-1)
        # You can set this as an env var or hardcode it if it's constant
        self.region = os.environ.get("AWS_REGION", "eu-central-1")
        self.bucket_name = os.environ.get("S3_BUCKET_NAME", "ling-ml-bucket")
        
        try:
            # Force Signature Version 4 (SigV4) and specify the region
            self.s3 = boto3.client(
                's3',
                region_name=self.region,
                config=Config(signature_version="s3v4")
            )
        except Exception as e:
            print(f"CloudStorage Init Warning: {e}")
            self.s3 = None

    def upload_file(self, local_path):
        """Upload a file to S3 and return a presigned download URL.

        Args:
            local_path: Absolute path to the local file to upload.

        Returns:
            A presigned S3 URL (48-hour expiry), or a mock URL if S3 is unavailable.
        """
        if not self.s3:
            return f"LOCAL_MOCK_URL_{os.path.basename(local_path)}"
            
        file_name = os.path.basename(local_path)
        try:
            # Use ContentDisposition to force browser download instead of playing in-browser

            logger.info("Start uploading file to AWS S3")
            self.s3.upload_file(
                local_path, 
                self.bucket_name, 
                file_name, 
                ExtraArgs={'ContentDisposition': f'attachment; filename="{file_name}"'}
            )
            
            # Generate the pre-signed URL using the SigV4 client
            url = self.s3.generate_presigned_url(
                'get_object', 
                Params={'Bucket': self.bucket_name, 'Key': file_name}, 
                ExpiresIn=172800
            )

            logger.info(f"Obtained url {url}")

            return url
        except Exception as e:
            print(f"Upload Error: {e}")
            return None