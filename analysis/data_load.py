# analysis/data_load.py
import pymongo
import pandas as pd

def load_collection(
    db_name: str,
    collection_name: str,
    mongo_uri: str = "mongodb://localhost:27017",
    sample_size: int = None
) -> pd.DataFrame:
    """
    Connects to MongoDB and loads either:
      - a random sample of `sample_size` documents (if sample_size is given), or
      - the entire collection (if sample_size is None).
    Drops the internal '_id' column.
    """
    client = pymongo.MongoClient(mongo_uri)
    coll   = client[db_name][collection_name]

    if sample_size is not None:
        # fetch only `sample_size` docs
        cursor = coll.aggregate([{"$sample": {"size": sample_size}}])
    else:
        cursor = coll.find()

    data = list(cursor)
    df = pd.DataFrame(data)
    if "_id" in df.columns:
        df.drop(columns=["_id"], inplace=True)
    return df
