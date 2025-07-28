import sys
from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy
from lib import ga_reporter

# --- Configuration ---
PROPERTY_ID = "280436820"
OUTPUT_PATH = "reports/campaign.html"
REPORT_TITLE = "Weekly Engaged Sessions by Campaign (Last 6 Weeks)"
TOP_N_CAMPAIGNS = 20

# Define custom colors for the top 5 campaigns
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

    # --- Calculate Date Range: 6 weeks ending last Saturday ---
    today = date.today()
    # weekday(): Monday is 0 and Sunday is 6. Saturday is 5.
    # Number of days to subtract to get to the most recent Saturday.
    days_since_saturday = (today.weekday() + 2) % 7
    end_date = today - timedelta(days=days_since_saturday)
    # Start date is 6 weeks (42 days) before the end date, inclusive.
    start_date = end_date - timedelta(days=41)

    campaign_date_ranges = [
        DateRange(start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
    ]

    # Define the request parameters
    dimensions = [
        Dimension(name="sessionCampaignName"),
        Dimension(name="sessionSourceMedium"),
        Dimension(name="date"),
    ]
    metrics = [Metric(name="engagedSessions")]
    order_bys = [
        OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"), desc=True),
        OrderBy(metric=OrderBy.MetricOrderBy(metric_name="engagedSessions"), desc=True),
    ]

    # Define campaigns to exclude from the report
    excluded_campaigns = {'(direct)', '(organic)', '(referral)', '(not set)'}

    # Run the report
    response = ga_reporter.run_ga_report(
        client, PROPERTY_ID, dimensions, metrics, order_bys, date_ranges=campaign_date_ranges
    )

    # Process data into a weekly DataFrame
    df = ga_reporter.process_to_weekly_df(
        response,
        key_dimension_indices=[0, 1],
        date_dimension_index=2,
        excluded_values=excluded_campaigns
    )

    # Set index names for the multi-level index
    df.index.names = ['Campaign', 'Source / Medium']

    if df.empty:
        print("No campaign data returned from API.")
        sys.exit()

    # --- Prepare data for chart and table ---
    df_for_table, df_for_chart = prepare_report_data(df, TOP_N_CAMPAIGNS)

    # --- Create Stacked Bar Chart with Plotly ---
    display_columns = [ga_reporter.format_week_header(d) for d in df_for_chart.columns]
    chart_html = create_chart(df_for_chart, display_columns)

    # --- Generate and save the final HTML file ---
    ga_reporter.generate_html_report(df_for_table, chart_html, REPORT_TITLE, OUTPUT_PATH, start_date, end_date)


def prepare_report_data(df, top_n):
    """Aggregates campaigns and prepares dataframes for table and chart."""
    # Aggregate smaller campaigns into "Others"
    df_aggregated = aggregate_campaigns(df, top_n)

    # Create a separate DataFrame for the chart (aggregated by campaign)
    df_for_chart = df_aggregated.groupby(level='Campaign').sum()

    # Create a separate DataFrame for the table with a 'Total' row
    df_for_table = df_aggregated.copy()
    df_for_table.loc[('Total', ''), :] = df_for_table.sum()

    return df_for_table, df_for_chart


def aggregate_campaigns(df, top_n):
    """Groups smaller campaigns into an 'Others' category."""
    most_recent_week = df.columns[0]
    campaign_totals = df.groupby(level='Campaign')[most_recent_week].sum().sort_values(ascending=False)

    if len(campaign_totals) <= top_n:
        return df.sort_values(by=most_recent_week, ascending=False)

    # Identify top N and other campaigns
    top_campaign_names = campaign_totals.head(top_n).index
    
    # Filter for top campaigns
    df_top = df[df.index.get_level_values('Campaign').isin(top_campaign_names)]

    # Filter for other campaigns to be aggregated
    df_others = df[~df.index.get_level_values('Campaign').isin(top_campaign_names)]
    others_sum = df_others.sum()

    # Rebuild the DataFrame with top campaigns and the 'Others' row
    df_aggregated = df_top.copy()
    df_aggregated.loc[('Others', ''), :] = others_sum

    # Sort the DataFrame by the original campaign total order, with 'Others' at the end
    sorted_campaign_order = top_campaign_names.tolist() + ['Others']
    return df_aggregated.reindex(sorted_campaign_order, level='Campaign')


def create_chart(df_chart, display_columns):
    """Creates a stacked bar chart from the DataFrame."""
    fig = go.Figure()

    # Iterate through the aggregated campaign data for the chart
    for i, campaign in enumerate(df_chart.index):
        # Assign a color from the list for the top campaigns, let Plotly handle the rest
        color = CAMPAIGN_COLORS[i] if i < len(CAMPAIGN_COLORS) else None
        fig.add_trace(go.Bar(
            x=display_columns,
            y=df_chart.loc[campaign],
            name=campaign,
            marker_color=color,
            hovertemplate=f'<b>{campaign}</b><br>Week: %{{x}}<br>Engaged Sessions: %{{y:,}}<extra></extra>',
        ))

    fig.update_layout(
        width=1080,
        height=800,
        barmode='stack',
        xaxis_title="Week (Sunday - Saturday)",
        yaxis_title="Engaged Sessions",
        legend_title="Campaigns",
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

if __name__ == "__main__":
    main()