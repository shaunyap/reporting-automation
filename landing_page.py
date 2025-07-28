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
OUTPUT_PATH = "reports/landing_page.html"
TOP_N_CHART = 15
TOP_N_TABLE = 20

# Re-using colors from overview.py for consistency
CHANNEL_COLORS = {
    'Direct': '#004b57',
    'Organic Search': '#00a0b2',
    'Paid Social': '#abb222',
    'Paid Search': '#FF736E',
    'Organic Social': ' #317a1c'
}


def main():
    """Main function to generate the landing page report."""
    client = ga_reporter.get_ga_client()

    # --- Calculate Date Range: week ending last Saturday ---
    today = date.today()
    days_since_saturday = (today.weekday() + 2) % 7
    end_date = today - timedelta(days=days_since_saturday)
    start_date = end_date - timedelta(days=6)

    landing_page_date_ranges = [
        DateRange(start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
    ]

    # Define the request parameters
    dimensions = [
        Dimension(name="landingPage"),
        Dimension(name=CUSTOM_CHANNEL_DIMENSION),
    ]
    metrics = [Metric(name="engagedSessions")]
    order_bys = [
        OrderBy(metric=OrderBy.MetricOrderBy(metric_name="engagedSessions"), desc=True),
    ]

    # Run the report
    response = ga_reporter.run_ga_report(
        client, PROPERTY_ID, dimensions, metrics, order_bys, date_ranges=landing_page_date_ranges
    )

    # Process data into an aggregated DataFrame
    df_agg = process_landing_page_data(response, excluded_values={'(not set)'})

    if df_agg.empty:
        print("No landing page data returned from API.")
        sys.exit()

    # --- Prepare data for chart and table ---
    # Get total sessions per landing page to determine the top N
    page_totals = df_agg.groupby(level='Landing Page')['Engaged Sessions'].sum().sort_values(ascending=False)

    top_chart_pages = page_totals.head(TOP_N_CHART).index
    df_for_chart = df_agg[df_agg.index.get_level_values('Landing Page').isin(top_chart_pages)]

    top_table_pages = page_totals.head(TOP_N_TABLE).index
    df_for_table = df_agg[df_agg.index.get_level_values('Landing Page').isin(top_table_pages)]

    # Define a dynamic report title
    report_title = f"Top Landing Pages by Engaged Sessions for Week Ending {end_date.strftime('%B %d, %Y')}"

    # --- Create Stacked Bar Chart with Plotly ---
    chart_html = create_landing_page_chart(df_for_chart)

    # --- Generate and save the final HTML file ---
    generate_landing_page_html_report(df_for_table, chart_html, report_title, OUTPUT_PATH, start_date, end_date)


def process_landing_page_data(response, excluded_values=None):
    """Processes GA API response into an aggregated DataFrame."""
    if excluded_values is None:
        excluded_values = set()

    report_data = []
    for row in response.rows:
        landing_page = row.dimension_values[0].value
        if landing_page in excluded_values:
            continue

        channel = row.dimension_values[1].value
        engaged_sessions = int(row.metric_values[0].value)

        report_data.append({
            'Landing Page': landing_page,
            'Channel': channel,
            'Engaged Sessions': engaged_sessions
        })

    if not report_data:
        return pd.DataFrame()

    df = pd.DataFrame(report_data)
    df = df.groupby(['Landing Page', 'Channel']).sum()

    # Sort by total sessions per landing page
    df = df.reindex(df.groupby(level='Landing Page')['Engaged Sessions'].sum().sort_values(ascending=False).index, level='Landing Page')

    return df


def create_landing_page_chart(df_chart):
    """Creates a stacked bar chart of landing pages by channel."""
    # Pivot data for stacking: index=Landing Page, columns=Channel, values=Engaged Sessions
    df_pivot = df_chart.unstack(level='Channel').fillna(0)
    df_pivot.columns = df_pivot.columns.droplevel(0)  # drop 'Engaged Sessions' from columns

    fig = go.Figure()

    # Sort channels by total sessions to stack largest at the bottom
    sorted_channels = df_pivot.sum().sort_values(ascending=False).index

    for channel in sorted_channels:
        fig.add_trace(go.Bar(
            x=df_pivot.index,
            y=df_pivot[channel],
            name=channel,
            marker_color=CHANNEL_COLORS.get(channel),
            hovertemplate='<b>%{x}</b><br>' + f'{channel}: %{{y:,}}<extra></extra>'
        ))

    fig.update_layout(
        width=1080,
        height=700,
        barmode='stack',
        xaxis_title="Landing Page",
        yaxis_title="Engaged Sessions",
        legend_title="Channels",
        template="plotly_white",
        xaxis={'categoryorder': 'total descending'},
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )
    # Shorten landing page URLs on x-axis for readability
    fig.update_xaxes(tickangle=45, tickfont=dict(size=10),
                     tickvals=df_pivot.index,
                     ticktext=[text if len(text) < 50 else text[:47] + '...' for text in df_pivot.index])

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def generate_landing_page_html_report(df_for_table, chart_html, report_title, output_path, start_date, end_date):
    """Generates and saves the final HTML report file for landing pages."""
    # Format the DataFrame for the HTML table
    df_display = df_for_table.copy()

    # Truncate long landing page URLs for display in the table
    original_index = df_display.index
    truncated_landing_pages = [
        lp if len(lp) <= 50 else lp[:50] + '...'
        for lp in original_index.get_level_values('Landing Page')
    ]
    df_display.index = pd.MultiIndex.from_arrays(
        [truncated_landing_pages, original_index.get_level_values('Channel')],
        names=original_index.names
    )

    # Format numeric columns with commas
    df_display['Engaged Sessions'] = df_display['Engaged Sessions'].apply(lambda x: f"{x:,.0f}")

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
