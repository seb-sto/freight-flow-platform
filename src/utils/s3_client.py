import boto3
from botocore.client import Config
import os

def get_minio_client():
    """Returns a boto s3 client pointed at local MinIO instance."""
    return boto3.client(
        "s3",
        endpoint_url=os.getenv["MINIO_ENDPOINT"],
        aws_access_key_id=os.getenv["MINIO_ROOT_USER"],
        aws_secret_access_key=os.getenv["MINIO_ROOT_PW"],
        config=Config(signature_version="s3s4"),
        region_name="us-east-1"
    )