import logging
import os
import tempfile
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from src.utils.s3_client import get_minio_client

load_dotenv()
logger = logging.getLogger(__name__)


def get_pg_conn():
    """Returns a psycopg2 connection to Postgres."""
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"]
    )


class BronzeToRawLoader:

    def __init__(self, minio_key: str, table_name: str, bucket: str = "bronze"):
        self.minio_key = minio_key
        self.table_name = table_name
        self.bucket = bucket

    def download_from_minio(self, tmp_path: str) -> None:
        client = get_minio_client()
        logger.info(f"Downloading s3://{self.bucket}/{self.minio_key} to {tmp_path}")
        client.download_file(self.bucket, self.minio_key, tmp_path)
        logger.info("Download complete")

    def load_to_postgres(self, tmp_path: str) -> None:
            conn = get_pg_conn()
            try:
                with conn.cursor() as cur:
                    # Truncate target table before loading
                    logger.info(f"Truncating raw.{self.table_name}")
                    cur.execute(f"TRUNCATE TABLE raw.{self.table_name}")

                    # Bulk load data via COPY
                    logger.info(f"Loading {tmp_path} into raw.{self.table_name}")
                    with open(tmp_path, "r") as f:
                        cur.copy_expert(
                            f"COPY raw.{self.table_name} FROM STDIN WITH CSV HEADER",
                            f
                        )

                    row_count = cur.rowcount
                    conn.commit()
                    logger.info(f"Loaded {row_count} rows into raw.{self.table_name}")
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def run(self) -> None:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                self.download_from_minio(tmp_path)
                self.load_to_postgres(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
                logger.info("Temp file cleaned up")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Load FAF data
    BronzeToRawLoader(
        minio_key="faf/2026/06/FAF5.7.1.csv",
        table_name="faf_shipments"
    ).run()

    # Load TransBorder data
    BronzeToRawLoader(
        minio_key="transborder/2026/04/transborder_dot2.csv",
        table_name="transborder_freight"
    ).run()

    # Load indicators data
    BronzeToRawLoader(
        minio_key="indicators/2026/07/supply_chain_indicators.csv",
        table_name="supply_chain_indicators"
    ).run()