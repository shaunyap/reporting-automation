import sys
import os
from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy
from lib import ga_reporter

# --- Configuration ---
PROPERTY_ID = "280436820"
CUSTOM_CHANNEL_DIMENSION = "sessionCustomChannelGroup:7871560290"
OUTPUT_PATH = "reports/overview.html"
REPORT_TITLE = "Weekly Engaged Sessions by Channel (Last 6 Weeks)"

# Define custom colors for specific channels for the chart
CHANNEL_COLORS = {
    'Direct': '#004b57',
    'Organic Search': '#00a0b2',
    'Paid Social': '#abb222',
    'Paid Search': '#FF736E',
    'Organic Social': ' #317a1c'
}


def main():
    """Main function to generate the overview report."""
    client = ga_reporter.get_ga_client()

    # --- Calculate Date Range: 6 weeks ending last Saturday ---
    today = date.today()
    # weekday(): Monday is 0 and Sunday is 6. Saturday is 5.
    # Number of days to subtract to get to the most recent Saturday.
    days_since_saturday = (today.weekday() + 2) % 7
    end_date = today - timedelta(days=days_since_saturday)
    # Start date is 6 weeks (42 days) before the end date, inclusive.
    start_date = end_date - timedelta(days=41)

    overview_date_ranges = [
        DateRange(start_date=start_date.strftime('%Y-%m-%d'),
                  end_date=end_date.strftime('%Y-%m-%d'))
    ]

    # Define the request parameters
    dimensions = [
        Dimension(name=CUSTOM_CHANNEL_DIMENSION),
        Dimension(name="date"),
    ]
    metrics = [Metric(name="engagedSessions")]
    order_bys = [
        OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"), desc=True),
        OrderBy(metric=OrderBy.MetricOrderBy(metric_name="engagedSessions"), desc=True),
    ]

    # Run the report
    response = ga_reporter.run_ga_report(
        client, PROPERTY_ID, dimensions, metrics, order_bys, date_ranges=overview_date_ranges
    )

    # Process data into a weekly DataFrame
    df = ga_reporter.process_to_weekly_df(
        response,
        key_dimension_indices=[0],
        date_dimension_index=1
    )

    if df.empty:
        print("No overview data returned from API.")
        sys.exit()

    # --- Prepare data for chart and table ---
    # Sort channels by engaged sessions in the most recent week (descending)
    most_recent_week = df.columns[0]
    df = df.sort_values(by=most_recent_week, ascending=False)

    # Create a separate DataFrame for the table with a 'Total' row
    df_for_table = df.copy()
    df_for_table.loc['Total'] = df_for_table.sum()

    # --- Create Stacked Bar Chart with Plotly ---
    display_columns = [ga_reporter.format_week_header(d) for d in df.columns]
    chart_html = create_chart(df, display_columns)

    # --- Fetch Summary Metrics for the last week ---
    summary_start_date = end_date - timedelta(days=6)
    summary_date_ranges = [
        DateRange(start_date=summary_start_date.strftime('%Y-%m-%d'),
                  end_date=end_date.strftime('%Y-%m-%d'))
    ]
    summary_metrics = [
        Metric(name="activeUsers"),
        Metric(name="engagedSessions"),
        Metric(name="keyEvents")
    ]

    summary_response = ga_reporter.run_ga_report(
        client,
        PROPERTY_ID,
        dimensions=[],
        metrics=summary_metrics,
        order_bys=[],
        date_ranges=summary_date_ranges
    )

    summary_stats = {"active_users": 0, "engaged_sessions": 0, "key_events": 0}
    if summary_response.rows:
        summary_stats["active_users"] = int(summary_response.rows[0].metric_values[0].value)
        summary_stats["engaged_sessions"] = int(summary_response.rows[0].metric_values[1].value)
        summary_stats["key_events"] = int(summary_response.rows[0].metric_values[2].value)

    # --- Fetch MTD Summary Metrics ---
    mtd_start_date = end_date.replace(day=1)
    mtd_date_ranges = [
        DateRange(start_date=mtd_start_date.strftime('%Y-%m-%d'),
                  end_date=end_date.strftime('%Y-%m-%d'))
    ]
    # The user asked for "Active Sessions", which we'll interpret as "engagedSessions" for consistency.
    mtd_metrics = [
        Metric(name="activeUsers"),
        Metric(name="engagedSessions")
    ]

    mtd_response = ga_reporter.run_ga_report(
        client,
        PROPERTY_ID,
        dimensions=[],
        metrics=mtd_metrics,
        order_bys=[],
        date_ranges=mtd_date_ranges
    )

    summary_stats["mtd_active_users"] = 0
    summary_stats["mtd_engaged_sessions"] = 0
    if mtd_response.rows:
        summary_stats["mtd_active_users"] = int(mtd_response.rows[0].metric_values[0].value)
        summary_stats["mtd_engaged_sessions"] = int(mtd_response.rows[0].metric_values[1].value)

    # --- Generate and save the final HTML file ---
    generate_overview_html_report(
        df_for_table, chart_html, REPORT_TITLE, OUTPUT_PATH, start_date, end_date, summary_stats
    )


def create_chart(df_chart, display_columns):
    """Creates a stacked bar chart from the DataFrame."""
    fig = go.Figure()

    for channel in df_chart.index:
        fig.add_trace(go.Bar(
            x=display_columns,
            y=df_chart.loc[channel],
            name=channel,
            marker_color=CHANNEL_COLORS.get(channel),
            hovertemplate=f'<b>{channel}</b><br>Week: %{{x}}<br>Engaged Sessions: %{{y:,}}<extra></extra>',
        ))

    fig.update_layout(
        width=1080,
        height=600,
        barmode='stack',
        xaxis_title="Week (Sunday - Saturday)",
        yaxis_title="Engaged Sessions",
        legend_title="Channels",
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def generate_overview_html_report(df_for_table, chart_html, report_title, output_path, start_date, end_date, summary_stats):
    """Generates and saves the final HTML report file for the overview."""
    # Format the DataFrame for the HTML table (add comma separators)
    df_display = df_for_table.copy()
    for col in df_display.columns:
        df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}")

    # Create formatted column headers for display
    display_columns = [ga_reporter.format_week_header(d) for d in df_for_table.columns]
    df_display.columns = display_columns

    table_html = df_display.to_html(classes='styled-table')
    table_html = table_html.replace(
        '<tr>\n      <th>Total</th>',
        '<tr class="total-row">\n      <th>Total</th>'
    )

    date_range_header = ""
    if start_date and end_date:
        start_formatted = start_date.strftime('%B %d, %Y')
        end_formatted = end_date.strftime('%B %d, %Y')
        date_range_header = f"<h2>{start_formatted} - {end_formatted}</h2>"

    # Create HTML for the summary stats
    summary_week_end = end_date
    summary_week_header = f"Summary for week ending {summary_week_end.strftime('%B %d, %Y')}"
    mtd_month_header = f"Month-to-Date Summary ({end_date.strftime('%B %Y')})"

    summary_html = f"""
    <div class="summary-stats">
        <h3>{summary_week_header}</h3>
        <p>Total active users: {summary_stats['active_users']:,}</p>
        <p>Total engaged sessions: {summary_stats['engaged_sessions']:,}</p>
        <p>Total key events: {summary_stats['key_events']:,}</p>

        <h3 style="margin-top: 20px;">{mtd_month_header}</h3>
        <p>MTD Active Users: {summary_stats['mtd_active_users']:,}</p>
        <p>MTD Engaged Sessions: {summary_stats['mtd_engaged_sessions']:,}</p>
    </div>
    """

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
    {summary_html}
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