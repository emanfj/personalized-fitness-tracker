# analysis/eda.py
import pandas as pd
import dtale
from .data_load import load_collection

def generate_dtale_report(
    db_name: str = "fitness_tracker",
    collection_name: str = "fitness_events",
    sample_size: int = 5000,
    host: str = "127.0.0.1",
    port: int = 40000
):
    """
    Loads a *sample* of the collection and launches D‑Tale for exploration.
    """
    # Directly sample in Mongo, not in pandas
    df = load_collection(db_name, collection_name, sample_size=sample_size)

    # Launch D‑Tale in your browser
    d = dtale.show(
        df,
        open_browser=True,
        host=host,
        port=port
    )
    print(f"\n➡️  D‑Tale server running! Open in browser: {d.main_url}\n")

    # Block until you hit Enter
    try:
        input("Press Enter to exit D‑Tale and continue... ")
    except KeyboardInterrupt:
        pass
