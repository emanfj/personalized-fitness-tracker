import pandas as pd
import json
import time
from kafka import KafkaProducer
from datetime import datetime
import random

def create_producer():
    return KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def stream_fitness_events():
    df = pd.read_parquet('data/fitness_events.parquet')
    producer = create_producer()
    
    print(f"Starting to stream {len(df)} events...")
    
    for _, row in df.iterrows():
        event = {
            'user_id': row['user_id'],
            'device_id': row['device_id'],
            'timestamp': row['event_ts'].isoformat() if pd.notna(row['event_ts']) else datetime.now().isoformat(),
            'event_type': row['activity_type'],
            'value': float(row['heart_rate_bpm']) if pd.notna(row['heart_rate_bpm']) else 0.0,
            'ingestion_time': datetime.now().isoformat()
        }

        
        producer.send('fitness-events', value=event)
        
        #simulate real-time streaming 
        time.sleep(random.uniform(0.1, 0.5))
        
        if _ % 100 == 0:
            print(f"Sent {_} events...")
    
    producer.flush()
    print("Finished streaming events")

if __name__ == "__main__":
    stream_fitness_events()