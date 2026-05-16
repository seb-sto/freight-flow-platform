from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class IngestorBase(ABC):
    """Base class for all data source ingestors"""

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def fetch(self) -> str:
        """Download raw data and save locally. Returns local file path."""
        pass

    @abstractmethod
    def validate_schema(self, file_path: str) -> bool:
        """Validate the downloaded file has the expected schema."""
        pass

    @abstractmethod
    def upload_to_bronze(self, file_path: str) -> str:
        """Upload validated file to MinIO bronze layer. Returns MinIO path."""
        pass

    def run_ingestion(self) -> str:
        """Orchestrate the full data ingestion: fetch data → validate schema → upload."""
        logger.info(f"Initiating ingestion for {self.source_name}")

        file_path = self.fetch()
        logger.info(f"Fetching data to: {file_path}")

        if not self.validate_schema(file_path):
            raise ValueError(f"Failed to validate schema for {self.source_name}")
        logger.info(f"Schema validation passed") 


        minio_path = self.upload_to_bronze(file_path)
        logger.info(f"Data uploaded to {minio_path}")

        return minio_path