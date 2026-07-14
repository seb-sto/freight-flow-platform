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


def run_bronze_silver_checkpoint() -> bool:
    """
    Validates raw.faf_shipments before dbt silver layer runs.
    Returns True if all expectations pass, False otherwise.
    """
    logger.info("Initializing GE context")
    context = gx.get_context()

    # Connect to Postgres
    datasource = context.data_sources.add_postgres(
        name="freight_postgres",
        connection_string=PG_CONNECTION_STRING
    )

    # Point to raw.faf_shipments table
    table_asset = datasource.add_table_asset(
        name="raw_faf_shipments",
        table_name="faf_shipments",
        schema_name="raw"
    )

    batch_definition = table_asset.add_batch_definition_whole_table(
        "faf_shipments_batch"
    )

    # Define expectation suite
    suite = context.suites.add(
        ExpectationSuite(name="bronze_silver_faf_suite")
    )

    # Expectations
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=1000000,
            max_value=10000000
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnToExist(column="dms_orig")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnToExist(column="dms_dest")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnToExist(column="sctg2")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnToExist(column="dms_mode")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="dms_orig")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="dms_dest")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="sctg2")
    )

    # Create validation definition
    validation_def = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="bronze_silver_faf_validation",
            data=batch_definition,
            suite=suite
        )
    )

    # Run checkpoint
    checkpoint = context.checkpoints.add(
        gx.Checkpoint(
            name="bronze_silver_checkpoint",
            validation_definitions=[validation_def]
        )
    )

    logger.info("Running bronze→silver GE checkpoint")
    result = checkpoint.run()

    if result.success:
        logger.info("✅ Bronze→Silver checkpoint passed")
    else:
        logger.error("❌ Bronze→Silver checkpoint FAILED")
        for validation_result in result.run_results.values():
            for expectation_result in validation_result.results:
                if not expectation_result.success:
                    logger.error(f"Failed: {expectation_result.expectation_config}")

    return bool(result.success)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = run_bronze_silver_checkpoint()
    exit(0 if success else 1)