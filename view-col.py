from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

spark = configure_spark_with_delta_pip(SparkSession.builder).getOrCreate()
spark.read.format('delta').load('lake/bronze/fitness_events').show(5)
spark.read.format('delta').load('lake/silver/fitness_aggregates').show(5)