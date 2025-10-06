from pyspark.sql.connect.client.core import SparkConnectGrpcException
from databricks.connect import DatabricksSession
from pyspark.sql import SparkSession
from pyprojroot import here

from concurrent.futures import ThreadPoolExecutor
import asyncio
import os


def create_directory(directory_path: str) -> None:
    """
    Create a directory if it does not exist.

    Parameters:
        directory_path (str): The path of the directory to be created.

    Example:
    ```python
    create_directory("/path/to/new/directory")
    ```

    """
    if not os.path.exists(here(directory_path)):
        os.makedirs(here(directory_path))


executor = ThreadPoolExecutor()
spark: SparkSession | None = None  # cached global session

def _new_spark_session() -> SparkSession:
    """Blocking init/reinit of SparkSession."""
    try:
        return DatabricksSession.builder.getOrCreate()
    except SparkConnectGrpcException:
        return DatabricksSession.builder.create()

async def get_spark_session_async() -> SparkSession:
    global spark
    loop = asyncio.get_event_loop()

    # If no session yet, create one
    if spark is None:
        spark = await loop.run_in_executor(executor, _new_spark_session)
        return spark

    # Validate session by running a trivial query
    try:
        await loop.run_in_executor(executor, lambda: spark.sql("SELECT 1").collect())
    except SparkConnectGrpcException:
        spark = await loop.run_in_executor(executor, _new_spark_session)

    return spark

def get_spark_session_sync() -> SparkSession:
    global spark
    if spark is None:
        spark = _new_spark_session()
    
    try:
        test_run = spark.sql("SELECT 1").collect()
    except SparkConnectGrpcException:
        spark = _new_spark_session()
    return spark