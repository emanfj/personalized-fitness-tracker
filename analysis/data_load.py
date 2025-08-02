# analysis/data_load.py

import pymongo
import pandas as pd

def load_collection(
    db_name: str,
    collection_name: str,
    mongo_uri: str = "mongodb://localhost:27017",
    user_filter: dict | None = None,
    sample_size: int | None = None
) -> pd.DataFrame:
    """
    Connects to MongoDB and loads *only* matching docs:
      • if user_filter is given, applies it as a $match
      • if sample_size is given, applies a $sample
    Drops the internal '_id' column.
    """
    client = pymongo.MongoClient(mongo_uri)
    coll   = client[db_name][collection_name]

    pipeline = []
    if user_filter:
        pipeline.append({"$match": user_filter})
    if sample_size is not None:
        pipeline.append({"$sample": {"size": sample_size}})
        cursor = coll.aggregate(pipeline)
    elif pipeline:
        cursor = coll.aggregate(pipeline)
    else:
        cursor = coll.find()

    docs = list(cursor)
    df   = pd.DataFrame(docs)
    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)
    return df
