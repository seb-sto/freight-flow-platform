import logging
import os
import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PG_CONNECTION_STRING = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:"
    f"{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:5432/"
    f"{os.environ['POSTGRES_DB']}"
)


def run_silver_gold_checkpoint() -> bool:
    """
    Validates silver.stg_faf_shipments before gold layer runs.
    Returns True if all expectations pass, False otherwise.
    """
    logger.info("Initializing GE context")
    context = gx.get_context()

    # Connect to Postgres
    datasource = context.data_sources.add_postgres(
        name="freight_postgres_silver",
        connection_string=PG_CONNECTION_STRING
    )

    # Point to silver.stg_faf_shipments view
    table_asset = datasource.add_table_asset(
        name="silver_faf_shipments",
        table_name="stg_faf_shipments",
        schema_name="silver"
    )

    batch_definition = table_asset.add_batch_definition_whole_table(
        "silver_faf_shipments_batch"
    )

    # Define expectation suite
    suite = context.suites.add(
        ExpectationSuite(name="silver_gold_faf_suite")
    )

    # Row count should match raw layer within 1%
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=2000000,
            max_value=3000000
        )
    )

    # Key columns must exist
    for column in ["shipment_id", "origin_zone", "destination_zone",
                   "commodity_code", "mode_code"]:
        suite.add_expectation(
            gx.expectations.ExpectColumnToExist(column=column)
        )

    # No nulls on key columns
    for column in ["shipment_id", "origin_zone", "destination_zone",
                   "commodity_code", "mode_code"]:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
        )

    # Shipment IDs must be unique
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="shipment_id")
    )

    # Tonnage values should be non-negative
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="tons_2024",
            min_value=0
        )
    )

    # Create validation definition
    validation_def = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="silver_gold_faf_validation",
            data=batch_definition,
            suite=suite
        )
    )

    # Run checkpoint
    checkpoint = context.checkpoints.add(
        gx.Checkpoint(
            name="silver_gold_checkpoint",
            validation_definitions=[validation_def]
        )
    )

    logger.info("Running silver→gold GE checkpoint")
    result = checkpoint.run()

    if result.success:
        logger.info("✅ Silver→Gold checkpoint passed")
    else:
        logger.error("❌ Silver→Gold checkpoint FAILED")
        for validation_result in result.run_results.values():
            for expectation_result in validation_result.results:
                if not expectation_result.success:
                    logger.error(
                        f"Failed: {expectation_result.expectation_config}"
                    )

    return bool(result.success)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = run_silver_gold_checkpoint()
    exit(0 if success else 1)