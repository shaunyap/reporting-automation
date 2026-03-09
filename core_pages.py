import sys
import os
from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
import re
from plotly.subplots import make_subplots
from lib import ga_reporter
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy

# --- Configuration ---
PROPERTY_ID = "280436820"
OUTPUT_PATH = "reports/core_pages.html"
TOP_N_CHART = 15
TOP_N_TABLE = 20

# Re-using colors from overview.py for consistency
BAR_CHART_COLOR = '#004b57'

# Define the regex for core page paths.
CORE_PAGE_REGEX = r"^(/|/pricing|/solutions/industries.*|/platform/.*customer.*|/contact-sales|.*/demo/request|.*/demo/|/customers|.*department.*|/capabilities/data.*|/capabilities/real.*)$"

# --- Define Segments as Dictionaries to Avoid Import Issues ---

# Filter for sessions that visited a core page, excluding 'thank-you' pages.
CORE_PAGE_VISIT_FILTER = {
    "and_group": {
        "expressions": [
            {"filter": {"field_name": "pagePath", "string_filter": {"match_type": "FULL_REGEXP", "value": CORE_PAGE_REGEX}}},
            {"not_expression": {"filter": {"field_name": "pagePath", "string_filter": {"match_type": "CONTAINS", "value": "thank-you"}}}}
        ]
    }
}

# Segment 1: Sessions that include a visit to any core page.
SESSION_WITH_CORE_PAGE_VISIT_SEGMENT = {
    "name": "sessions_with_core_page_visit",
    "session_segment": {
        "session_filter": {"filter_expression": CORE_PAGE_VISIT_FILTER}
    }
}

# Segment 2: Sessions that include a visit to a core page AND a key event anywhere in the session.
SESSION_WITH_CORE_PAGE_AND_KEY_EVENT_SEGMENT = {
    "name": "sessions_with_core_page_and_key_event",
    "session_segment": {
        "session_filter": {
            "filter_expression": {
                "and_group": {
                    "expressions": [
                        CORE_PAGE_VISIT_FILTER,
                        {"filter": {"field_name": "eventName", "string_filter": {"match_type": "EXACT", "value": "key_event"}}}
                    ]
                }
            }
        }
    }
}


def main():
    """Main function to generate the core pages report."""
    client = ga_reporter.get_ga_client()

    # --- Calculate Date Range: previous Sunday to most recent Saturday ---
    today = date.today()
    # weekday(): Monday is 0 and Sunday is 6.
    # Go back to the most recent Saturday.
    days_since_saturday = (today.weekday() - 5 + 7) % 7 + 1
    end_date = today - timedelta(days=days_since_saturday)
    start_date = end_date - timedelta(days=6) # This will be the preceding Sunday

    date_ranges = [
        DateRange(start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
    ]

    # --- Run two reports using segments ---
    # 1. Get engaged sessions per page, for sessions that visited a core page.
    response_all_sessions = ga_reporter.run_ga_report(
        client,
        PROPERTY_ID,
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="engagedSessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="engagedSessions"), desc=True)],
        date_ranges=date_ranges,
        segment=SESSION_WITH_CORE_PAGE_VISIT_SEGMENT
    )
    df_all_sessions = process_ga_response(response_all_sessions, 'Engaged Sessions')

    # 2. Get engaged sessions per page, for sessions that visited a core page AND had a key event.
    response_conversion_sessions = ga_reporter.run_ga_report(
        client,
        PROPERTY_ID,
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="engagedSessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="engagedSessions"), desc=True)],
        date_ranges=date_ranges,
        segment=SESSION_WITH_CORE_PAGE_AND_KEY_EVENT_SEGMENT
    )
    df_conversion_sessions = process_ga_response(
        response_conversion_sessions,
        'Sessions with Key Event'
    )

    # --- Merge the two DataFrames ---
    if df_all_sessions.empty:
        print("No core page data returned from API for the 'all sessions' segment.")
        sys.exit()

    df = pd.merge(df_all_sessions, df_conversion_sessions, on='Page Path', how='left').fillna(0)
    # Convert the merged column to integer
    df['Sessions with Key Event'] = df['Sessions with Key Event'].astype(int)
    # Calculate conversion rate
    df['Conversion Rate'] = (df['Sessions with Key Event'] / df['Engaged Sessions']).fillna(0)

    # --- Prepare data for chart and table ---
    # Sort by engaged sessions for consistent ordering
    df_sorted = df.sort_values(by='Engaged Sessions', ascending=False)

    # The API calls already filtered to core pages, so we can use the entire result for the chart.
    df_for_chart = df_sorted
    df_for_table = df_sorted.head(TOP_N_TABLE)

    # Define the title that will be used for the H1 header
    report_title = f"Core Page Conversions for Week Ending {end_date.strftime('%B %d, %Y')}"

    # --- Create Performance Chart with Plotly ---
    chart_html = create_core_pages_chart(df_for_chart)

    # --- Generate and save the final HTML file ---
    generate_core_pages_html_report(df_for_table, chart_html, report_title, OUTPUT_PATH, start_date, end_date)


def process_ga_response(response, metric_name):
    """Processes a GA API response for a single metric into a DataFrame."""
    # The segment in the API call already filters for the correct sessions,
    # but we still need to filter the returned pagePaths to only include core pages.
    report_data = []
    for row in response.rows:
        page_path = row.dimension_values[0].value
        # Double-check that the returned page path matches our core page definition.
        # This is necessary because the session segment includes the whole session if any page matches,
        # so the response will contain all pages from those sessions.
        if not re.match(CORE_PAGE_REGEX, page_path, re.IGNORECASE) or 'thank-you' in page_path:
            continue

        sessions = int(row.metric_values[0].value)

        report_data.append({
            'Page Path': page_path,
            metric_name: sessions
        })

    if not report_data:
        return pd.DataFrame()

    return pd.DataFrame(report_data)


def create_core_pages_chart(df_chart):
    """Creates a combined bar and line chart for core pages."""
    # Create figure with a secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Truncate long page paths for display on the x-axis
    chart_labels = [
        path if len(path) <= 50 else path[:47] + '...'
        for path in df_chart['Page Path']
    ]

    # Add Bar Chart for Engaged Sessions
    fig.add_trace(
        go.Bar(
            x=chart_labels,
            y=df_chart['Engaged Sessions'],
            name='Engaged Sessions',
            marker_color=BAR_CHART_COLOR,
            hovertemplate='<b>%{x}</b><br>Engaged Sessions: %{y:,}<extra></extra>'
        ),
        secondary_y=False,
    )

    # Add Line Chart for Sessions with Key Event
    fig.add_trace(
        go.Scatter(
            x=chart_labels,
            y=df_chart['Sessions with Key Event'],
            name='Sessions with Key Event',
            mode='lines+markers',
            line=dict(color='#d62728'),
            hovertemplate='<b>%{x}</b><br>Sessions with Key Event: %{y:,}<extra></extra>'
        ),
        secondary_y=True,
    )

    # Set titles and layout
    fig.update_layout(
        width=1080,
        xaxis_title="Page Path",
        legend_title="Metrics",
        template="plotly_white",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Set y-axes titles
    fig.update_yaxes(title_text="<b>Engaged Sessions</b>", secondary_y=False, rangemode="tozero")
    fig.update_yaxes(title_text="<b>Sessions with Key Event</b>", secondary_y=True, rangemode="tozero")

    # Rotate x-axis labels for better readability
    fig.update_xaxes(tickangle=45, tickfont=dict(size=10))

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def generate_core_pages_html_report(df_for_table, chart_html, report_title, output_path, start_date, end_date):
    """Generates and saves the final HTML report file for core pages data."""
    # Format the DataFrame for the HTML table
    df_display = df_for_table.set_index('Page Path')

    # Truncate long page paths for display in the table
    truncated_index = [
        path if len(path) <= 60 else path[:57] + '...'
        for path in df_display.index
    ]
    df_display.index = pd.Index(truncated_index, name='Page Path')

    # Format numeric columns
    df_display['Engaged Sessions'] = df_display['Engaged Sessions'].apply(lambda x: f"{x:,.0f}")
    df_display['Sessions with Key Event'] = df_display['Sessions with Key Event'].apply(lambda x: f"{x:,.0f}")
    df_display['Conversion Rate'] = df_display['Conversion Rate'].apply(lambda x: f"{x:.2%}")

    
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