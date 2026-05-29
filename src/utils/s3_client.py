import boto3
from botocore.client import Config
import os
from dotenv import load_dotenv

load_dotenv()

def get_minio_client():
    """Returns a boto s3 client pointed at local MinIO instance."""
    return boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        config=Config(signature_version="s3v4"),
        region_name="us-east-1"
    )