from analysis.data_load import load_collection
from analysis.eda import generate_dtale_report
from analysis.aggregate import weekly_aggregation
from analysis.clustering_anomaly import perform_clustering, detect_anomalies
from analysis.weekly_report import generate_weekly_markdown

if __name__ == "__main__":
    # 1) EDA report
    generate_dtale_report()

    # 2) Load raw events and aggregate weekly
    events = load_collection("fitness_tracker", "fitness_events")
    weekly = weekly_aggregation(events)

    # 3) Clustering & anomaly detection
    clustered, _ = perform_clustering(weekly, n_clusters=4)
    anomaly_df, _ = detect_anomalies(weekly, contamination=0.02)

    # 4) Write markdown summary
    generate_weekly_markdown(weekly, clustered, anomaly_df)
    print("Analysis complete — reports in analysis/ folder.")
