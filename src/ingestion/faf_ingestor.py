import logging
import zipfile
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone
import subprocess

from src.ingestion.base import IngestorBase
from src.utils.s3_client import get_minio_client
from src.utils.manifest import append_manifest_entry, compute_sha256


logger=logging.getLogger(__name__)

DL_URL = "https://faf.ornl.gov/faf5/data/download_files/FAF5.7.1.zip"

EXPECTED_COLUMNS = {
    "fr_orig", "dms_orig", "dms_dest", "fr_dest",
    "dms_mode", "sctg2", "trade_type",
    "tons_2017", "tons_2024",
    "value_2017", "value_2024",
    "tmiles_2017", "tmiles_2024"
}

DOWNLOAD_DIR = Path("data/raw")

class FAFIngestor(IngestorBase):

    def __init__(self):
        super().__init__(source_name="faf5")

    def fetch(self) -> str:
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = DOWNLOAD_DIR / "FAF5.7.1.zip"

        logger.info(f"Downloading FAF5 data from {DL_URL}")
        subprocess.run([
            "curl",
            "-L",           # follow redirects
            "-o", str(zip_path),  # output path
            "--retry", "3", # retry up to 3 times
            DL_URL
        ], check=True)

        logger.info("Extracting ZIP archive")
        with zipfile.ZipFile(zip_path, "r") as zf:
            csv_files = [f for f in zf.namelist() if f.endswith(".csv")]
            if not csv_files:
                raise FileNotFoundError("No CSV found in FAF5 ZIP archive")
            zf.extract(csv_files[0], DOWNLOAD_DIR)
            csv_path = DOWNLOAD_DIR / csv_files[0]

        logger.info(f"Extracted to {csv_path}")
        return str(csv_path)


    def validate_schema(self, file_path: str) -> bool:
        logger.info(f"Validating schema for {file_path}")
        df = pd.read_csv(file_path, nrows=0)
        file_columns = set(df.columns)
        missing_columns = EXPECTED_COLUMNS - file_columns

        if missing_columns:
            logger.error(f"Missing columns detected: {missing_columns}")
            return False

        logger.info("Schema validation passed")
        return True

    def upload_to_bronze(self, file_path: str) -> str:
        client = get_minio_client()
        bucket = "bronze"

        # Check if bucket exist. If not, create a new one
        try:
            client.head_bucket(Bucket=bucket)
        except client.exceptions.ClientError:
            logger.info(f"Creating bucket: {bucket}")
            client.create_bucket(Bucket=bucket)


        file_hash = compute_sha256(file_path)

        # Build unique MinIO path with timestamp
        now = datetime.now(timezone.utc)
        minio_key = f"faf/{now.year}/{now.month:02d}/FAF5.7.1.csv"

        # Check if file with same hash already exists
        try:
            existing = client.head_object(Bucket=bucket, Key=minio_key)
            if existing["Metadata"].get("sha256") == file_hash:
                logger.info("File unchanged, skipping upload")
                append_manifest_entry(
                    source=self.source_name,
                    source_url=DL_URL,
                    filename="FAF5.7.1.csv",
                    minio_path=f"s3://{bucket}/{minio_key}",
                    row_count=self._get_row_count(file_path),
                    sha256=file_hash,
                    skipped=True
                )
                return f"s3://{bucket}/{minio_key}"
        except client.exceptions.ClientError:
            pass # File doesn't exist, proceed with upload

        logger.info(f"Uploading to s3://{bucket}/{minio_key}")
        client.upload_file(
            file_path,
            bucket,
            minio_key,
            ExtraArgs={"Metadata": {"sha256": file_hash}}
        )
        append_manifest_entry(
            source=self.source_name,
            source_url=DL_URL,
            filename="FAF5.7.1.csv",
            minio_path=f"s3://{bucket}/{minio_key}",
            row_count=self._get_row_count(file_path),
            sha256=file_hash,
            skipped=False
        )
        logger.info("Upload complete")
        return f"s3://{bucket}/{minio_key}"
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    ingestor = FAFIngestor()
    ingestor.run_ingestion()