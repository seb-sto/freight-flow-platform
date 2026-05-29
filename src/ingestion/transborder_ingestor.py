import logging
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from src.ingestion.base import IngestorBase
from src.utils.url_builder import build_transborder_urls
from src.utils.s3_client import get_minio_client
from src.utils.manifest import compute_sha256

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path("data/raw/transborder")

EXPECTED_COLUMNS = {
    "TRDTYPE", "USASTATE", "COMMODITY2",
    "DISAGMOT", "COUNTRY", "VALUE",
    "SHIPWT", "MONTH", "YEAR"
}


class TransBorderIngestor(IngestorBase):

    def __init__(self, year: int, month: int):
        super().__init__(source_name="transborder")
        self.year = year
        self.month = month

    def fetch(self) -> str:
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = DOWNLOAD_DIR / f"transborder_{self.year}_{self.month:02d}.zip"

        # Check if file already downloaded manually
        if zip_path.exists():
            logger.info(f"Using locally available file: {zip_path}")
        else:
            logger.warning(
                f"File not found locally: {zip_path}\n"
                f"Please download manually from:\n"
                f"https://www.bts.gov/topics/transborder-raw-data\n"
                f"And save to: {zip_path}"
            )
            raise FileNotFoundError(f"Manual download required: {zip_path}")

        # Extract dot2 CSV from ZIP
        logger.info("Extracting ZIP archive")
        with zipfile.ZipFile(zip_path, "r") as zf:
            dot2_files = [f for f in zf.namelist() if "dot2" in f.lower() and f.endswith(".csv")]
            if not dot2_files:
                raise FileNotFoundError("No dot2 CSV found in TransBorder ZIP archive")
            zf.extract(dot2_files[0], DOWNLOAD_DIR)
            csv_path = DOWNLOAD_DIR / dot2_files[0]

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

        # Build unique MinIO path for correct month and year
        minio_key = f"transborder/{self.year}/{self.month:02d}/transborder_dot2.csv"

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
    import logging
    logging.basicConfig(level=logging.INFO)

    now = datetime.now(timezone.utc)
    ingestor = TransBorderIngestor(year=now.year, month=now.month - 2)
    ingestor.run_ingestion()