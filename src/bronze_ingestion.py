from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from delta import configure_spark_with_delta_pip

def create_spark_session():
    builder = SparkSession.builder \
        .appName("FitnessTracker-Bronze") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    
    return configure_spark_with_delta_pip(builder).getOrCreate()

def setup_kafka_stream(spark):
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "fitness-events") \
        .option("startingOffsets", "latest") \
        .load()
    
    # schema for fitness events
    fitness_schema = StructType([
        StructField("user_id", StringType(), True),
        StructField("device_id", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("value", DoubleType(), True),
        StructField("ingestion_time", StringType(), True)
    ])
    
    #parse JSON and add metadata
    parsed_df = kafka_df.select(
        from_json(col("value").cast("string"), fitness_schema).alias("data"),
        col("timestamp").alias("kafka_timestamp"),
        col("partition"),
        col("offset")
    ).select(
        col("data.*"),
        col("kafka_timestamp"),
        col("partition"),
        col("offset"),
        current_timestamp().alias("bronze_ingestion_time")
    )
    
    return parsed_df

def write_to_bronze(df):
    return df.writeStream \
        .format("delta") \
        .outputMode("append") \
        .option("checkpointLocation", "lake/_checkpoints/bronze") \
        .option("path", "lake/bronze/fitness_events") \
        .trigger(processingTime='30 seconds') \
        .start()

def main():
    spark = create_spark_session()
    
    try:
        print("Setting up Kafka stream...")
        stream_df = setup_kafka_stream(spark)
        
        print("Starting bronze layer ingestion...")
        query = write_to_bronze(stream_df)
        
        print("Bronze ingestion running... Press Ctrl+C to stop")
        query.awaitTermination()
        
    except KeyboardInterrupt:
        print("Stopping bronze ingestion...")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()