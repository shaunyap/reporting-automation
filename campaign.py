import os
from collections import defaultdict
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)

# Set the path to your service account key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./.env/credentials.json"

# Your GA4 Property ID
property_id = "280436820"

# Instantiate the client
client = BetaAnalyticsDataClient()

# Define the request for the report
request = RunReportRequest(
    property=f"properties/{property_id}",
    dimensions=[
        Dimension(name="sessionCampaignName"),
        Dimension(name="sessionSourceMedium"),
        Dimension(name="date"),
    ],
    metrics=[Metric(name="engagedSessions")],
    date_ranges=[
        # Fetch data for the last 6 weeks
        DateRange(start_date="42daysAgo", end_date="yesterday")
    ],
    order_bys=[
        # Order by date descending to process most recent dates first
        OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"), desc=True),
        OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name="engagedSessions"),
            desc=True,
        ),
    ],
)


# Run the report
response = client.run_report(request)

# --- Process data for pivot table ---
# Use a nested defaultdict to easily sum sessions per week for each campaign
pivoted_data = defaultdict(lambda: defaultdict(int))

# Define campaigns to exclude
excluded_campaigns = {'(direct)', '(organic)', '(referral)', '(not set)'}

for row in response.rows:
    campaign = row.dimension_values[0].value
    source_medium = row.dimension_values[1].value
    # Skip excluded campaigns
    if campaign in excluded_campaigns:
        continue

    date_str = row.dimension_values[2].value
    sessions = int(row.metric_values[0].value)

    # Convert date string (e.g., "20231225") to a datetime object
    current_date = datetime.strptime(date_str, "%Y%m%d").date()

    # Calculate the start of the week (Sunday) for the given date
    # In Python's weekday(), Monday is 0 and Sunday is 6.
    days_since_sunday = (current_date.weekday() + 1) % 7
    week_start_date = current_date - timedelta(days=days_since_sunday)

    pivoted_data[(campaign, source_medium)][week_start_date] += sessions

# --- Convert data to a pandas DataFrame for easier manipulation ---
df = pd.DataFrame.from_dict(pivoted_data, orient='index')

# Set index names for the multi-level index
df.index.names = ['Campaign', 'Source / Medium']

# If no data, exit gracefully
if df.empty:
    print("No data returned from API.")
    exit()

# Get the 6 most recent weeks, sort them, and filter the DataFrame
all_weeks = sorted(df.columns, reverse=True)
sorted_weeks = all_weeks[:6]
df = df[sorted_weeks]

# Fill any missing data with 0 and convert to integer
df = df.fillna(0).astype(int)

# --- Prepare data for chart and table ---

# Sort campaigns by engaged sessions in the most recent week (descending)
most_recent_week = sorted_weeks[0]

# --- Aggregate smaller campaigns into "Others" ---
TOP_N = 20
# Group by campaign to get total sessions for sorting and aggregation
campaign_totals = df.groupby(level='Campaign')[most_recent_week].sum().sort_values(ascending=False)

if len(campaign_totals) > TOP_N:
    # Identify top N and other campaigns
    top_campaign_names = campaign_totals.head(TOP_N).index
    
    # Filter for top campaigns
    df_top = df[df.index.get_level_values('Campaign').isin(top_campaign_names)]

    # Filter for other campaigns to be aggregated
    df_others = df[~df.index.get_level_values('Campaign').isin(top_campaign_names)]
    others_sum = df_others.sum()

    # Rebuild the DataFrame with top campaigns and the 'Others' row
    df = df_top.copy()
    df.loc[('Others', ''), :] = others_sum

    # Sort the DataFrame by the original campaign total order, with 'Others' at the end
    sorted_campaign_order = top_campaign_names.tolist() + ['Others']
    df = df.reindex(sorted_campaign_order, level='Campaign')

# --- Prepare data for chart (aggregated by campaign) ---
df_for_chart = df.groupby(level='Campaign').sum()

# Add a 'Total' row at the bottom
df.loc[('Total', ''), :] = df.sum()

# Create formatted column headers for display (e.g., "Dec 25 - Dec 31")
def format_week_header(start_date):
    end_date = start_date + timedelta(days=6)
    return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"

display_columns = [format_week_header(d) for d in df.columns]


# --- Create Stacked Bar Chart with Plotly ---

fig = go.Figure()

# Iterate through the aggregated campaign data for the chart
for campaign in df_for_chart.index:
    fig.add_trace(go.Bar(
        x=display_columns,
        y=df_for_chart.loc[campaign],
        name=campaign,
        hovertemplate=f'<b>{campaign}</b><br>Week: %{{x}}<br>Engaged Sessions: %{{y:,}}<extra></extra>',
    ))

fig.update_layout(
    height=800,
    barmode='stack',
    title_text='Weekly Engaged Sessions by Campaign (Last 6 Weeks)',
    xaxis_title="Week (Sunday - Saturday)",
    yaxis_title="Engaged Sessions",
    legend_title="Campaigns",
    template="plotly_white"
)

# --- Generate HTML content ---

# Convert the figure to an HTML div
chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

# Format the DataFrame for the HTML table (add comma separators)
df_display = df.copy()
for col in df_display.columns:
    df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}")

# Rename columns to the display format and set index name
df_display.columns = display_columns

# Convert the DataFrame to an HTML table string
table_html = df_display.to_html(classes='styled-table')

# --- Create and save the final HTML file ---
html_template = f"""
<html>
<head>
    <title>Campaign Analytics Report</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <h1>Google Analytics Weekly Campaign Report</h1>

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

output_dir = "reports"
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "campaign.html")
with open(output_path, "w") as f:
    f.write(html_template)

print(f"Report successfully generated: {output_path}")