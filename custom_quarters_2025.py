import sys
import os
from google.analytics.data_v1beta.types import DateRange, Metric
from lib import ga_reporter

# --- Configuration ---
PROPERTY_ID = "280436820"
OUTPUT_PATH = "reports/custom_quarters_2025.html"

def main():
    """Generates a report for specific custom quarters in 2025."""
    client = ga_reporter.get_ga_client()

    # Define the custom quarters requested
    # Feb - Apr 2025
    # Apr - Jun 2025
    quarters = [
        {
            "name": "Feb 1 - Apr 30, 2025",
            "start_date": "2025-02-01",
            "end_date": "2025-04-30"
        },
        {
            "name": "Apr 1 - Jun 30, 2025",
            "start_date": "2025-04-01",
            "end_date": "2025-06-30"
        }
    ]

    metrics = [
        Metric(name="activeUsers"),
        Metric(name="engagedSessions"),
        Metric(name="keyEvents")
    ]

    results = []

    print(f"Fetching data for Property ID: {PROPERTY_ID}...")
    print("-" * 80)
    print(f"{'Period':<30} | {'Active Users':<15} | {'Engaged Sessions':<18} | {'Key Events':<15}")
    print("-" * 80)

    for q in quarters:
        date_ranges = [
            DateRange(start_date=q["start_date"], end_date=q["end_date"])
        ]
        
        # Run the report with no dimensions to get totals
        response = ga_reporter.run_ga_report(
            client,
            PROPERTY_ID,
            dimensions=[], 
            metrics=metrics,
            order_bys=[],
            date_ranges=date_ranges
        )

        active_users = 0
        engaged_sessions = 0
        key_events = 0

        if response.rows:
            active_users = int(response.rows[0].metric_values[0].value)
            engaged_sessions = int(response.rows[0].metric_values[1].value)
            key_events = int(response.rows[0].metric_values[2].value)

        results.append({
            "name": q["name"],
            "active_users": active_users,
            "engaged_sessions": engaged_sessions,
            "key_events": key_events
        })

        print(f"{q['name']:<30} | {active_users:<15,} | {engaged_sessions:<18,} | {key_events:<15,}")

    # Generate simple HTML report
    generate_html(results)


def generate_html(results):
    """Generates a simple HTML table with the results."""
    rows_html = ""
    for r in results:
        rows_html += f"""
        <tr>
            <td>{r['name']}</td>
            <td>{r['active_users']:,}</td>
            <td>{r['engaged_sessions']:,}</td>
            <td>{r['key_events']:,}</td>
        </tr>
        """

    html_content = f"""
<html>
<head>
    <title>Custom Quarterly Report 2025</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #004b57; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 800px; margin-top: 20px; }}
        th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; color: #004b57; }}
        tr:hover {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>Custom Quarterly Report 2025</h1>
    <table>
        <thead>
            <tr>
                <th>Period</th>
                <th>Active Users</th>
                <th>Engaged Sessions</th>
                <th>Key Events</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</body>
</html>
    """
    
    output_dir = os.path.dirname(OUTPUT_PATH)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
    with open(OUTPUT_PATH, "w") as f:
        f.write(html_content)
    
    print("-" * 80)
    print(f"HTML report saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()