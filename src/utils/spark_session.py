"""PySpark session factory with Delta Lake support."""

from pyspark.sql import SparkSession

from src.utils.config import get_config


def get_spark(app_name: str = "HealthcareLakehouse") -> SparkSession:
    """Create or retrieve a SparkSession configured for Delta Lake."""
    config = get_config()

    spark = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.warehouse.dir", str(config.bronze_path / "spark-warehouse"))
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "4")  # small data, fewer partitions
        .master("local[*]")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    return spark
