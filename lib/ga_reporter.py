import os
from collections import defaultdict
from datetime import datetime, timedelta
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, RunReportRequest


def get_ga_client(credentials_path="./.env/credentials.json"):
    """Instantiates and returns a GA4 BetaAnalyticsDataClient."""
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    return BetaAnalyticsDataClient()


def run_ga_report(client, property_id, dimensions, metrics, order_bys, date_ranges=None):
    """Runs a report against the Google Analytics Data API v1."""
    if date_ranges is None:
        date_ranges = [DateRange(start_date="42daysAgo", end_date="yesterday")]

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=dimensions,
        metrics=metrics,
        date_ranges=date_ranges,
        order_bys=order_bys,
    )
    return client.run_report(request)


def process_to_weekly_df(response, key_dimension_indices, date_dimension_index, metric_index=0, excluded_values=None):
    """Processes GA API response into a weekly pivoted DataFrame."""
    if excluded_values is None:
        excluded_values = set()

    pivoted_data = defaultdict(lambda: defaultdict(int))

    for row in response.rows:
        # Create a key from the specified dimension values
        key_parts = [row.dimension_values[i].value for i in key_dimension_indices]

        # Skip if the first key part is in the exclusion list
        if key_parts and key_parts[0] in excluded_values:
            continue

        key = tuple(key_parts) if len(key_parts) > 1 else key_parts[0]

        date_str = row.dimension_values[date_dimension_index].value
        sessions = int(row.metric_values[metric_index].value)

        current_date = datetime.strptime(date_str, "%Y%m%d").date()
        days_since_sunday = (current_date.weekday() + 1) % 7
        week_start_date = current_date - timedelta(days=days_since_sunday)

        pivoted_data[key][week_start_date] += sessions

    df = pd.DataFrame.from_dict(pivoted_data, orient='index')

    if df.empty:
        return df

    # Get the 6 most recent weeks, sort them, and filter the DataFrame
    all_weeks = sorted(df.columns, reverse=True)
    sorted_weeks = all_weeks[:6]
    df = df[sorted_weeks]

    return df.fillna(0).astype(int)


def format_week_header(start_date):
    """Formats a date object into a 'Mon Day - Mon Day' string."""
    end_date = start_date + timedelta(days=6)
    return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"


def generate_html_report(df_for_table, chart_html, report_title, output_path, start_date=None, end_date=None):
    """Generates and saves the final HTML report file."""
    # Format the DataFrame for the HTML table (add comma separators)
    df_display = df_for_table.copy()
    for col in df_display.columns:
        df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}")

    # Create formatted column headers for display
    display_columns = [format_week_header(d) for d in df_for_table.columns]
    df_display.columns = display_columns

    table_html = df_display.to_html(classes='styled-table')

    date_range_header = ""
    if start_date and end_date:
        start_formatted = start_date.strftime('%B %d, %Y')
        end_formatted = end_date.strftime('%B %d, %Y')
        date_range_header = f"<h2>{start_formatted} - {end_formatted}</h2>"

    html_template = f"""
<html>
<head>
    <title>{report_title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <h1>{report_title}</h1>
    {date_range_header}
    {chart_html}
    {table_html}
</body>
</html>
"""

    # Add a class to the 'Total' row for styling
    html_template = html_template.replace(
        '<tr>\n      <th>Total</th>',
        '<tr class="total-row">\n      <th>Total</th>'
    )

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(html_template)

    print(f"Report successfully generated: {output_path}")