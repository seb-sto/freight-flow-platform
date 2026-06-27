FROM apache/airflow:2.9.0-python3.11

USER root
RUN apt-get update && apt-get install -y \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy only necessary project files
COPY --chown=airflow:root pyproject.toml .
COPY --chown=airflow:root src/ ./src/
COPY --chown=airflow:root dbt/ ./dbt/

# Install dependencies
RUN pip install --no-cache-dir \
    boto3==1.34.0 \
    pandas==2.2.0 \
    psycopg2-binary \
    python-dotenv \
    sqlalchemy \
    "great-expectations>=0.18.0" \
    dbt-core \
    dbt-postgres