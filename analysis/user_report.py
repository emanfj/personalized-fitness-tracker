import os
from pathlib import Path
import pandas as pd
from datetime import datetime
import time
from .data_load import load_collection

def _compute_weekly(df: pd.DataFrame, ts_col: str, aggs: dict):
    print(f"  ▶ resampling '{ts_col}' into weekly buckets…")
    
    # Handle empty DataFrame
    if df.empty:
        print(f"    → DataFrame is empty, returning empty weekly DataFrame")
        # Create an empty DataFrame with the expected columns from aggs
        empty_weekly = pd.DataFrame(columns=list(aggs.keys()))
        empty_weekly.index = pd.DatetimeIndex([], freq='W')
        return empty_weekly
    
    df = df.copy()
    df[ts_col] = pd.to_datetime(df[ts_col])
    df.set_index(ts_col, inplace=True)
    weekly = df.resample("W").agg(aggs)
    weekly.index = weekly.index.to_period("W").start_time
    print(f"    → got {len(weekly)} weekly rows")
    return weekly


def generate_user_report(
    user_id: str,
    db_name: str = "fitness_tracker",
    output_dir: str = "analysis/user_reports"
):
    """
    Loads all streams for a user, computes weekly aggregates,
    and writes a Markdown summary + simple recommendations.
    """
    print(f"\n=== Generating report for user {user_id} ===")
    t0 = time.time()

    # 1) load per-user data
    print("  ▶ loading fitness_events…")
    events = load_collection(
        db_name,
        "fitness_events",
        user_filter={"user_id": user_id}
    )
    print(f"    → loaded {len(events)} events for this user")

    print("  ▶ loading sleep_sessions…")
    sleep = load_collection(
        db_name,
        "sleep_sessions",
        user_filter={"user_id": user_id}
    )
    print(f"    → loaded {len(sleep)} sleep sessions")

    print("  ▶ loading nutrition_logs…")
    nutrition = load_collection(
        db_name,
        "nutrition_logs",
        user_filter={"user_id": user_id}
    )
    print(f"    → loaded {len(nutrition)} nutrition logs")

    print("  ▶ loading feedback_events…")
    feedback = load_collection(
        db_name,
        "feedback_events",
        user_filter={"user_id": user_id}
    )
    print(f"    → loaded {len(feedback)} feedback events")

    # 2) aggregate per stream
    wk_events = _compute_weekly(
        events,
        ts_col="event_ts",
        aggs={
            "step_increment":"sum",
            "duration_s":"mean",
            "heart_rate_bpm":"mean",
            "event_id":"count"
        }
    ).rename(columns={
        "event_id":"workout_count",
        "duration_s":"avg_duration_s",
        "heart_rate_bpm":"avg_hr"
    })

    wk_sleep = _compute_weekly(
        sleep,
        ts_col="end_ts",
        aggs={"quality":"mean", "session_id":"count"}
    ).rename(columns={
        "quality":"avg_sleep_quality",
        "session_id":"sleep_sessions"
    })

    wk_nutri = _compute_weekly(
        nutrition,
        ts_col="log_ts",
        aggs={"calories":"sum", "log_id":"count"}
    ).rename(columns={"log_id":"meals_logged"})

    wk_feedback = _compute_weekly(
        feedback,
        ts_col="event_ts",
        aggs={"energy":"mean", "perceived_exertion":"mean"}
    ).rename(columns={
        "energy":"avg_energy",
        "perceived_exertion":"avg_exertion"
    })

    # 3) merge
    print("  ▶ merging weekly dataframes…")
    weekly = pd.concat([wk_events, wk_sleep, wk_nutri, wk_feedback], axis=1).fillna(0)
    print(f"    → final weekly shape: {weekly.shape}")

    # 4) compute recommendations - handle case where weekly might be empty
    print("  ▶ generating recommendations…")
    recs = []
    
    if not weekly.empty:
        latest = weekly.iloc[-1]
        if latest.workout_count < 3:
            recs.append(f"- Only {int(latest.workout_count)} workouts last week. Aim for ≥ 3.")
        if hasattr(latest, 'avg_sleep_quality') and latest.avg_sleep_quality < 0.7:
            recs.append(f"- Sleep quality {latest.avg_sleep_quality:.2f}. Try wind‑down routine.")
        if hasattr(latest, 'step_increment') and latest.step_increment < 5000:
            avg_steps = int(latest.step_increment / max(latest.workout_count,1))
            recs.append(f"- Avg {avg_steps} steps per workout—consider extra walks.")
        if not recs:
            recs.append("- 🎉 Great job! No recommendations 🎉")
    else:
        recs.append("- No data available for analysis. Start tracking your activities!")

    # 5) write HTML report
    print("  ▶ writing HTML report…")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    html_path = Path(output_dir) / f"{user_id}_weekly.html"
    
    # Create HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Fitness Report - {user_id}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f7fa;
            color: #333;
        }}
        .header {{
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        .section h2 {{
            color: #4a5568;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 0.9em;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background-color: #f7fafc;
            font-weight: 600;
            color: #4a5568;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background-color: #f7fafc;
        }}
        .metric-card {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin: 5px;
            min-width: 150px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 1.8em;
            font-weight: bold;
            display: block;
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .recommendations {{
            background: #f0fff4;
            border-left: 4px solid #48bb78;
        }}
        .recommendations ul {{
            list-style: none;
            padding: 0;
        }}
        .recommendations li {{
            padding: 10px 0;
            border-bottom: 1px solid #e6fffa;
        }}
        .recommendations li:last-child {{
            border-bottom: none;
        }}
        .recommendations li:before {{
            content: "💡 ";
            margin-right: 8px;
        }}
        .positive-rec:before {{
            content: "🎉 ";
        }}
        .warning-rec {{
            background: #fff5f5;
            border-left-color: #f56565;
        }}
        .warning-rec li:before {{
            content: "⚠️ ";
        }}
        .no-data {{
            text-align: center;
            color: #718096;
            font-style: italic;
            padding: 20px;
        }}
        .date-column {{
            font-weight: 600;
            color: #667eea;
        }}
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .header h1 {{ font-size: 1.8em; }}
            table {{ font-size: 0.8em; }}
            .metric-card {{ min-width: 120px; margin: 2px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Weekly Fitness Report</h1>
        <div class="subtitle">User: {user_id}</div>
        <div class="subtitle">Generated: {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}</div>
    </div>
    
    <div class="section">
        <h2>📊 Weekly Summary</h2>"""
    
    if not weekly.empty:
        # Add summary metrics cards
        latest = weekly.iloc[-1]
        html_content += f"""
        <div style="margin: 20px 0;">
            <div class="metric-card">
                <span class="metric-value">{int(latest.workout_count)}</span>
                <span class="metric-label">Workouts</span>
            </div>
            <div class="metric-card">
                <span class="metric-value">{int(latest.step_increment):,}</span>
                <span class="metric-label">Total Steps</span>
            </div>
            <div class="metric-card">
                <span class="metric-value">{latest.avg_hr:.0f}</span>
                <span class="metric-label">Avg Heart Rate</span>
            </div>
            <div class="metric-card">
                <span class="metric-value">{latest.avg_duration_s/60:.0f}</span>
                <span class="metric-label">Avg Duration (min)</span>
            </div>
        </div>"""
        
        # Convert DataFrame to HTML table with better formatting
        html_table = weekly.to_html(
            float_format=lambda x: f"{x:.2f}" if x != 0 else "0",
            table_id="summary-table",
            classes="",
            escape=False
        )
        
        # Clean up the table HTML and add date formatting
        html_table = html_table.replace('<th></th>', '<th class="date-column">Week Starting</th>')
        html_content += html_table
    else:
        html_content += '<div class="no-data">No weekly data available.</div>'
    
    html_content += '</div>'
    
    # Recommendations section
    rec_class = "recommendations"
    if any("Sleep quality 0.00" in rec or "Only" in rec for rec in recs):
        rec_class += " warning-rec"
    
    html_content += f"""
    <div class="section {rec_class}">
        <h2>💡 Recommendations</h2>
        <ul>"""
    
    for rec in recs:
        rec_item_class = "positive-rec" if "🎉" in rec else ""
        clean_rec = rec.replace("- ", "").replace("🎉 ", "")
        html_content += f'<li class="{rec_item_class}">{clean_rec}</li>'
    
    html_content += """
        </ul>
    </div>
    
    <div class="section" style="text-align: center; color: #718096; font-size: 0.9em;">
        <p>This report was automatically generated by your fitness tracking system.</p>
    </div>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"  → report saved to {html_path}")
    print(f"Done in {time.time() - t0:.2f}s")
    return html_path