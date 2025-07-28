def generate_weekly_markdown(
    agg_df,
    clustered_df,
    anomaly_df,
    output_path: str = "analysis/weekly_report.md"
):
    """
    Writes a simple markdown report summarizing:
      - aggregated weekly metrics
      - cluster distribution
      - anomaly counts
    """
    with open(output_path, "w") as f:
        f.write("# Weekly Fitness Report\n\n")

        f.write("## Aggregated Metrics\n\n")
        f.write(agg_df.to_markdown())
        f.write("\n\n")

        f.write("## Cluster Distribution\n\n")
        dist = clustered_df["cluster"].value_counts().sort_index()
        f.write(dist.to_markdown())
        f.write("\n\n")

        f.write("## Anomaly Summary\n\n")
        anom = anomaly_df["anomaly"].map({1: "normal", -1: "anomaly"}).value_counts()
        f.write(anom.to_markdown())
        f.write("\n")
