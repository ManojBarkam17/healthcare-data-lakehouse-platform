"""PySpark session factory with Delta Lake support.

Uses delta-spark pip package (configure_spark_with_delta_pip)
instead of Maven JAR downloads for reliable cross-platform setup.
"""

import os
import platform
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

from src.utils.config import get_config


def _setup_hadoop_windows() -> None:
    """Auto-configure Hadoop home on Windows if not already set.

    PySpark on Windows requires winutils.exe from Hadoop.
    This looks for a local hadoop/ directory in the project root,
    or falls back to HADOOP_HOME env var.
    """
    if platform.system() != "Windows":
        return

    # Already configured
    if os.environ.get("HADOOP_HOME") and Path(os.environ["HADOOP_HOME"], "bin", "winutils.exe").exists():
        return

    # Check project-local hadoop dir (created by setup_hadoop_win.ps1)
    project_root = Path(__file__).resolve().parent.parent.parent
    local_hadoop = project_root / "hadoop"
    if (local_hadoop / "bin" / "winutils.exe").exists():
        os.environ["HADOOP_HOME"] = str(local_hadoop)
        os.environ["PATH"] = str(local_hadoop / "bin") + os.pathsep + os.environ.get("PATH", "")
        return

    # Check common install location
    common_path = Path("C:/hadoop")
    if (common_path / "bin" / "winutils.exe").exists():
        os.environ["HADOOP_HOME"] = str(common_path)
        os.environ["PATH"] = str(common_path / "bin") + os.pathsep + os.environ.get("PATH", "")
        return


def get_spark(app_name: str = "HealthcareLakehouse") -> SparkSession:
    """Create or retrieve a SparkSession configured for Delta Lake.

    Uses delta-spark pip package for Delta Lake support — no Maven
    downloads needed. Works reliably on Windows, macOS, and Linux.
    """
    _setup_hadoop_windows()
    config = get_config()

    builder = (
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
    )

    # Point Spark to local Hadoop on Windows
    hadoop_home = os.environ.get("HADOOP_HOME")
    if hadoop_home:
        builder = builder.config("spark.hadoop.home.dir", hadoop_home)

    # Use pip-installed Delta JARs instead of Maven download
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
