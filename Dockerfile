FROM apache/airflow:2.9.0-python3.11

# Switch to root to install system dependencies
USER root

RUN apt-get update && apt-get install -y \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch back to airflow user for pip installs
USER airflow

# Copy dependency file
COPY pyproject.toml .

# Install project dependencies
RUN pip install --no-cache-dir \
    boto3==1.34.0 \
    pandas==2.2.0 \
    psycopg2-binary \
    python-dotenv \
    sqlalchemy \
    great-expectations>=0.18.0 \
    dbt-core \
    dbt-postgres