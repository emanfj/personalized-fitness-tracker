from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from delta import configure_spark_with_delta_pip
import pyspark.sql.functions as F

def create_spark_session():
    builder = SparkSession.builder \
        .appName("FitnessTracker-Silver") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    
    return configure_spark_with_delta_pip(builder).getOrCreate()

def create_silver_aggregates(spark):
    #reading from bronze as a stream
    bronze_df = spark \
        .readStream \
        .format("delta") \
        .load("lake/bronze/fitness_events")
    
    # 5-minute windowed aggregations
    silver_df = bronze_df \
        .withColumn("event_timestamp", to_timestamp(col("timestamp"))) \
        .groupBy(
            window(col("event_timestamp"), "5 minutes"),
            col("user_id"),
            col("device_id"),
            col("event_type")
        ) \
        .agg(
            count("*").alias("event_count"),
            avg("value").alias("avg_value"),
            min("value").alias("min_value"),
            max("value").alias("max_value"),
            stddev("value").alias("stddev_value"),
            first("bronze_ingestion_time").alias("first_seen"),
            max("bronze_ingestion_time").alias("last_seen")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("user_id"),
            col("device_id"),
            col("event_type"),
            col("event_count"),
            col("avg_value"),
            col("min_value"),
            col("max_value"),
            col("stddev_value"),
            col("first_seen"),
            col("last_seen"),
            current_timestamp().alias("silver_processed_time")
        )
    
    return silver_df

def write_to_silver(df):
    return df.writeStream \
        .format("delta") \
        .outputMode("update") \
        .option("checkpointLocation", "lake/_checkpoints/silver") \
        .option("path", "lake/silver/fitness_aggregates") \
        .trigger(processingTime='1 minute') \
        .start()

def main():
    spark = create_spark_session()
    
    try:
        print("Creating silver layer aggregations...")
        silver_df = create_silver_aggregates(spark)
        
        print("Starting silver layer processing...")
        query = write_to_silver(silver_df)
        
        print("Silver processing running... Press Ctrl+C to stop")
        query.awaitTermination()
        
    except KeyboardInterrupt:
        print("Stopping silver processing...")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()