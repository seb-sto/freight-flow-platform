import logging
import zipfile
import httpx
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from dotenv import load_dotenv
from src.ingestion.base import IngestorBase
from src.utils.s3_client import get_minio_client
from src.utils.manifest import compute_sha256

load_dotenv()
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
        with httpx.Client(follow_redirects=True, timeout=120) as client:
            response = client.get(DL_URL)
            response.raise_for_status()
            zip_path.write_bytes(response.content)
        
        logger.info("Extracting .zip archive")
        with zipfile.ZipFile(zip_path, "r") as zf:
            csv_files = [f for f in zf.namelist() if f.endswith(".csv")]
            if not csv_files:
                raise FileNotFoundError("No .csv file found in FAF5 .zip archive")
            zf.extract(csv_files[0], DOWNLOAD_DIR)
            csv_path = DOWNLOAD_DIR / csv_files[0]
        
        logger.info(f"Extracted data to {csv_path}")
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
        file_hash = compute_sha256(file_path)

        # Build unique MinIO path with timestamp
        now = datetime.now(timezone.utc)
        minio_key = f"faf/{now.year}/{now.month:02d}/FAF5.7.1.csv"

        # Check if file with same hash already exists
        try:
            existing = client.head_object(Bucket=bucket, Key=minio_key)
            if existing["Metadata"].get("sha256") == file_hash:
                logger.info("File unchanged, skipping upload")
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

        logger.info("Upload complete")
        return f"s3://{bucket}/{minio_key}"
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    ingestor = FAFIngestor()
    ingestor.run_ingestion()