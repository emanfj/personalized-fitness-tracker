from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest

def perform_clustering(
    df,
    n_clusters: int = 3,
    random_state: int = 42
):
    """
    Applies KMeans clustering to all numeric columns of df.
    """
    X = df.select_dtypes(include="number").dropna(axis=1)
    model = KMeans(n_clusters=n_clusters, random_state=random_state)  # k‑means++ initialization :contentReference[oaicite:5]{index=5}
    labels = model.fit_predict(X)  # standard usage :contentReference[oaicite:6]{index=6}
    clustered = df.copy()
    clustered["cluster"] = labels
    return clustered, model

def detect_anomalies(
    df,
    contamination: float = 0.01,
    random_state: int = 42
):
    """
    Uses IsolationForest to flag anomalies in numeric columns.
    """
    X = df.select_dtypes(include="number").dropna(axis=1)
    iso = IsolationForest(
        contamination=contamination,
        random_state=random_state
    )  # ensemble of isolation trees :contentReference[oaicite:7]{index=7}
    isof_labels = iso.fit_predict(X)
    ana = df.copy()
    ana["anomaly"] = isof_labels  # -1 for outliers, 1 for inliers :contentReference[oaicite:8]{index=8}
    return ana, iso
