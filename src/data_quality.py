from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from delta import configure_spark_with_delta_pip
import json
from datetime import datetime

def create_spark_session():
    builder = SparkSession.builder \
        .appName("FitnessTracker-DataQuality") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    
    return configure_spark_with_delta_pip(builder).getOrCreate()

def run_bronze_quality_checks(spark):
    """Run quality checks on bronze layer"""
    df = spark.read.format("delta").load("lake/bronze/fitness_events")
    
    checks = {}
    
    #basic counts
    checks['total_records'] = df.count()
    checks['unique_users'] = df.select('user_id').distinct().count()
    checks['unique_devices'] = df.select('device_id').distinct().count()
    
    #null checks
    checks['null_user_ids'] = df.filter(col('user_id').isNull()).count()
    checks['null_timestamps'] = df.filter(col('timestamp').isNull()).count()
    checks['null_values'] = df.filter(col('value').isNull()).count()
    
    #val range checks
    checks['negative_values'] = df.filter(col('value') < 0).count()
    checks['extreme_values'] = df.filter(col('value') > 1000).count()
    
    #timestamp checks
    df_with_ts = df.withColumn('parsed_timestamp', to_timestamp(col('timestamp')))
    checks['invalid_timestamps'] = df_with_ts.filter(col('parsed_timestamp').isNull()).count()
    
    return checks

def run_silver_quality_checks(spark):
    """Run quality checks on silver layer"""
    try:
        df = spark.read.format("delta").load("lake/silver/fitness_aggregates")
        
        checks = {}
        checks['total_aggregates'] = df.count()
        checks['avg_events_per_window'] = df.agg(avg('event_count')).collect()[0][0]
        checks['windows_with_zero_events'] = df.filter(col('event_count') == 0).count()
        
        return checks
    except Exception as e:
        return {'error': str(e)}

def main():
    spark = create_spark_session()
    
    try:
        print("Running Bronze Layer Quality Checks...")
        bronze_checks = run_bronze_quality_checks(spark)
        
        print("Running Silver Layer Quality Checks...")
        silver_checks = run_silver_quality_checks(spark)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'bronze_checks': bronze_checks,
            'silver_checks': silver_checks
        }
        
        print("\n=== DATA QUALITY REPORT ===")
        print(json.dumps(report, indent=2))
        
        with open(f"dq_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(report, f, indent=2)
            
    finally:
        spark.stop()

if __name__ == "__main__":
    main()