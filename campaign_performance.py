import sys
import os
from datetime import date, timedelta
from collections import defaultdict
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy
from lib import ga_reporter

# --- Configuration ---
PROPERTY_ID = "280436820"
OUTPUT_PATH = "reports/campaign_performance.html"
TOP_N_CHART = 10
TOP_N_TABLE = 20

# Define custom colors for the top campaigns
CAMPAIGN_COLORS = [
    '#004b57',
    '#00a0b2',
    '#abb222',
    '#FF736E',
    '#317a1c'
]


def main():
    """Main function to generate the campaign report."""
    client = ga_reporter.get_ga_client()

    # --- Calculate Date Range: week ending last Saturday ---
    today = date.today()
    # weekday(): Monday is 0 and Sunday is 6. Saturday is 5.
    # Number of days to subtract to get to the most recent Saturday.
    days_since_saturday = (today.weekday() + 2) % 7
    end_date = today - timedelta(days=days_since_saturday)
    # Start date is 1 week (7 days) before the end date, inclusive.
    start_date = end_date - timedelta(days=6)

    campaign_date_ranges = [
        DateRange(start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
    ]

    # Define the request parameters
    dimensions = [
        Dimension(name="sessionCampaignName"),
        Dimension(name="sessionSourceMedium"),
    ]
    metrics = [
        Metric(name="engagedSessions"),
        Metric(name="keyEvents")
    ]
    order_bys = [
        OrderBy(metric=OrderBy.MetricOrderBy(metric_name="engagedSessions"), desc=True),
    ]

    # Define campaigns to exclude from the report
    excluded_campaigns = {'(direct)', '(organic)', '(referral)', '(not set)'}

    # Run the report
    response = ga_reporter.run_ga_report(
        client, PROPERTY_ID, dimensions, metrics, order_bys, date_ranges=campaign_date_ranges
    )

    # Process data into a weekly DataFrame
    df_agg = process_performance_data(response, excluded_campaigns)

    if df_agg.empty:
        print("No campaign performance data returned from API.")
        sys.exit()

    # --- Prepare data for chart and table ---
    df_for_chart = df_agg.head(TOP_N_CHART)
    df_for_table = df_agg.head(TOP_N_TABLE)

    # Define the title that will be used for the H1 header
    chart_title = f"Top {TOP_N_CHART} Campaigns Performance for Week Ending {end_date.strftime('%B %d, %Y')}"

    # --- Create Performance Chart with Plotly ---
    chart_html = create_performance_chart(df_for_chart)

    # --- Generate and save the final HTML file ---
    generate_performance_html_report(df_for_table, chart_html, chart_title, OUTPUT_PATH, start_date, end_date)


def process_performance_data(response, excluded_values=None):
    """Processes GA API response into an aggregated DataFrame."""
    if excluded_values is None:
        excluded_values = set()

    report_data = []
    for row in response.rows:
        campaign = row.dimension_values[0].value
        if campaign in excluded_values:
            continue

        source_medium = row.dimension_values[1].value
        engaged_sessions = int(row.metric_values[0].value)
        key_events = int(row.metric_values[1].value)

        report_data.append({
            'Campaign': campaign,
            'Source / Medium': source_medium,
            'Engaged Sessions': engaged_sessions,
            'Key Events': key_events
        })

    if not report_data:
        return pd.DataFrame()

    # Convert to DataFrame and set multi-level index
    df = pd.DataFrame(report_data)
    df = df.set_index(['Campaign', 'Source / Medium'])

    # Calculate Key Event Rate, handle division by zero
    df['Key Event Rate'] = (df['Key Events'] / df['Engaged Sessions']).fillna(0)

    # The API response is already sorted, but we sort again to be safe
    df = df.sort_values(by='Engaged Sessions', ascending=False)

    return df


def create_performance_chart(df_chart):
    """Creates a combined bar and line chart for top campaigns."""
    # Create figure with a secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Create a display name for the x-axis (e.g., "Campaign Name\n(Source/Medium)")
    chart_labels = [f"{idx[0]}<br>({idx[1]})" for idx in df_chart.index]

    # Add Bar Chart for Engaged Sessions to the primary y-axis
    fig.add_trace(
        go.Bar(
            x=chart_labels,
            y=df_chart['Engaged Sessions'],
            name='Engaged Sessions',
            marker_color=CAMPAIGN_COLORS,  # Plotly will cycle through the colors
            hovertemplate='<b>%{x}</b><br>Engaged Sessions: %{y:,}<extra></extra>'
        ),
        secondary_y=False,
    )

    # Add Line Chart for Key Events to the secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=chart_labels,
            y=df_chart['Key Events'],
            name='Key Events',
            mode='lines+markers',
            line=dict(color='#d62728'),  # A distinct color for the line
            hovertemplate='<b>%{x}</b><br>Key Events: %{y:,}<extra></extra>'
        ),
        secondary_y=True,
    )

    # Set titles and layout
    fig.update_layout(
        width=1080,
        xaxis_title="Campaign",
        legend_title="Metrics",
        template="plotly_white",
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Set y-axes titles
    fig.update_yaxes(title_text="<b>Engaged Sessions</b>", secondary_y=False)
    fig.update_yaxes(title_text="<b>Key Events</b>", secondary_y=True)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def generate_performance_html_report(df_for_table, chart_html, report_title, output_path, start_date, end_date):
    """Generates and saves the final HTML report file for performance data."""
    # Format the DataFrame for the HTML table
    df_display = df_for_table.copy()

    # Format numeric columns with commas and rate column as percentage
    df_display['Engaged Sessions'] = df_display['Engaged Sessions'].apply(lambda x: f"{x:,.0f}")
    df_display['Key Events'] = df_display['Key Events'].apply(lambda x: f"{x:,.0f}")
    df_display['Key Event Rate'] = df_display['Key Event Rate'].apply(lambda x: f"{x:.2%}")

    table_html = df_display.to_html(classes='styled-table')

    # Format date range for display
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
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(html_template)

    print(f"Report successfully generated: {output_path}")


if __name__ == "__main__":
    main()