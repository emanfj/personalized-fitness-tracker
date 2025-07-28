import pandas as pd

def weekly_aggregation(
    df: pd.DataFrame,
    date_col: str = "event_ts",
    agg_funcs: dict = None
) -> pd.DataFrame:
    """
    Converts the timestamp column to datetime, sets it as index,
    and resamples on a weekly basis.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], unit="ms")  # or omit unit if ISO strings :contentReference[oaicite:3]{index=3}
    df.set_index(date_col, inplace=True)
    if agg_funcs is None:
        agg_funcs = {
            "heart_rate_bpm": ["mean", "std"],
            "step_increment": "sum",
            "calories_burned": "sum"
        }
    weekly = df.resample("W").agg(agg_funcs)  # weekly downsampling :contentReference[oaicite:4]{index=4}
    # flatten MultiIndex columns
    weekly.columns = ["_".join(col) for col in weekly.columns]
    return weekly
