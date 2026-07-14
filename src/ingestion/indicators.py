import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from src.ingestion.base import IngestorBase
from src.utils.s3_client import get_minio_client
from src.utils.manifest import compute_sha256, append_manifest_entry

load_dotenv()
logger = logging.getLogger(__name__)

INDICATORS_URL = "https://data.bts.gov/api/views/bw6n-ddqk/rows.csv?accessType=DOWNLOAD"
DOWNLOAD_DIR = Path("data/raw/indicators")

EXPECTED_COLUMNS = {
    "OBS_DATE", "TSI_Freight", "VMT",
    "RAIL_FRT_CARLOADS", "PETROLEUM", "WATERBORNE", "INV_TO_SALES"
}


class IndicatorsIngestor(IngestorBase):

    def __init__(self):
        super().__init__(source_name="supply_chain_indicators")

    def fetch(self) -> str:
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = DOWNLOAD_DIR / "supply_chain_indicators.csv"

        logger.info(f"Downloading indicators from {INDICATORS_URL}")
        subprocess.run([
            "curl", "-L", "-o", str(csv_path),
            "--retry", "3",
            INDICATORS_URL
        ], check=True)

        logger.info(f"Downloaded to {csv_path}")
        return str(csv_path)

    def validate_schema(self, file_path: str) -> bool:
        import pandas as pd

        logger.info(f"Validating schema for {file_path}")
        df = pd.read_csv(file_path, nrows=0)
        actual_columns = set(df.columns)
        missing_columns = EXPECTED_COLUMNS - actual_columns

        if missing_columns:
            logger.error(f"Missing columns: {missing_columns}")
            return False

        logger.info("Schema validation passed")
        return True

    def upload_to_bronze(self, file_path: str) -> str:
        client = get_minio_client()
        bucket = "bronze"

        try:
            client.head_bucket(Bucket=bucket)
        except client.exceptions.ClientError:
            logger.info(f"Creating bucket: {bucket}")
            client.create_bucket(Bucket=bucket)

        file_hash = compute_sha256(file_path)
        now = datetime.now(timezone.utc)
        minio_key = f"indicators/{now.year}/{now.month:02d}/supply_chain_indicators.csv"

        try:
            existing = client.head_object(Bucket=bucket, Key=minio_key)
            if existing["Metadata"].get("sha256") == file_hash:
                logger.info("File unchanged, skipping upload")
                append_manifest_entry(
                    source=self.source_name,
                    source_url=INDICATORS_URL,
                    filename="supply_chain_indicators.csv",
                    minio_path=f"s3://{bucket}/{minio_key}",
                    row_count=self._get_row_count(file_path),
                    sha256=file_hash,
                    skipped=True
                )
                return f"s3://{bucket}/{minio_key}"
        except client.exceptions.ClientError:
            pass

        logger.info(f"Uploading to s3://{bucket}/{minio_key}")
        client.upload_file(
            file_path, bucket, minio_key,
            ExtraArgs={"Metadata": {"sha256": file_hash}}
        )
        append_manifest_entry(
            source=self.source_name,
            source_url=INDICATORS_URL,
            filename="supply_chain_indicators.csv",
            minio_path=f"s3://{bucket}/{minio_key}",
            row_count=self._get_row_count(file_path),
            sha256=file_hash,
            skipped=False
        )
        logger.info("Upload complete")
        return f"s3://{bucket}/{minio_key}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingestor = IndicatorsIngestor()
    ingestor.run_ingestion()