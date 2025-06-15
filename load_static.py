# load_static.py  (Windows-friendly version)
from pyspark.sql import SparkSession
import os, pathlib

spark = (SparkSession.builder
         .appName("bronze-load")
         .config("spark.sql.extensions","io.delta.sql.DeltaSparkSessionExtension")
         .config("spark.sql.catalog.spark_catalog","org.apache.spark.sql.delta.catalog.DeltaCatalog")
         .getOrCreate())

# absolute path to lake/bronze  (adjust your drive & folder)
BRONZE = pathlib.Path("lake/bronze").resolve().as_uri()   # e.g. 'file:///D:/job apps/.../lake/bronze'

for name in ["users","devices","sleep_sessions","nutrition_logs","feedback_events"]:
    (spark.read.option("header",True)
          .csv(f"data/{name}.csv")
          .write.format("delta").mode("overwrite")
          .save(f"{BRONZE}/{name}"))

spark.stop()
