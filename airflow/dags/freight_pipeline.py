from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="freight_pipeline",
    default_args=default_args,
    description="End-to-end freight data pipeline",
    schedule_interval="@weekly",
    start_date=days_ago(1),
    catchup=False,
    tags=["freight", "pipeline"],
) as dag:

    # Task 1: Ingest FAF data
    ingest_faf = BashOperator(
        task_id="ingest_faf",
        bash_command="cd /opt/airflow && python -m src.ingestion.faf_ingestor",
    )

    # Task 2: Ingest TransBorder data
    ingest_transborder = BashOperator(
        task_id="ingest_transborder",
        bash_command="cd /opt/airflow && python -m src.ingestion.transborder_ingestor",
    )

    # Task 3: Bronze→Silver quality gate
    bronze_silver_check = BashOperator(
        task_id="bronze_silver_quality_check",
        bash_command="cd /opt/airflow && python -m src.quality.bronze_silver_checkpoint",
    )

    # Task 4: Run dbt silver models
    dbt_silver = BashOperator(
        task_id="dbt_silver",
        bash_command="cd /opt/airflow/dbt/freight_flow && dbt run --select staging",
    )

    # Task 5: Silver→Gold quality gate
    silver_gold_check = BashOperator(
        task_id="silver_gold_quality_check",
        bash_command="cd /opt/airflow && python -m src.quality.silver_gold_checkpoint",
    )

    # Task 6: Run dbt gold models (Week 5)
    dbt_gold = BashOperator(
        task_id="dbt_gold",
        bash_command="cd /opt/airflow/dbt/freight_flow && dbt run --select marts",
    )

    # Define task dependencies
    [ingest_faf, ingest_transborder] >> bronze_silver_check >> dbt_silver >> silver_gold_check >> dbt_gold