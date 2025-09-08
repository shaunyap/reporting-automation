import datetime
import os
import sys
import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import yaml

# --- Configuration ---
# The customer ID is retrieved from the google-ads.yaml file.
OUTPUT_PATH = "reports/paid_efficiency.html"


def main():
    """Main function to generate the paid efficiency report."""
    # Define config_path outside the try block for access in the exception handler.
    config_path = os.path.join(os.path.dirname(__file__), ".env", "google-ads.yaml")
    try:
        # Load configuration from YAML file and initialize the Google Ads client.
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        client = GoogleAdsClient.load_from_dict(config)
        customer_id = config.get('customer_id')
        if not customer_id:
            print("Error: 'customer_id' not found in google-ads.yaml.", file=sys.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, yaml.YAMLError, ValueError) as e:
        print(f"Error in configuration file '{os.path.basename(config_path)}': {e}", file=sys.stderr)
        sys.exit(1)
    except GoogleAdsException as ex:
        print(f"Error initializing Google Ads client: {ex}", file=sys.stderr)
        sys.exit(1)

    # Get date range for the report (week ending last Saturday)
    start_date, end_date = get_week_range()

    # Fetch campaign spend data from the API
    df_spend = fetch_campaign_spend(client, str(customer_id), start_date, end_date)

    # If no data is returned, print a message and exit gracefully.
    if df_spend.empty:
        print("No campaign spend data returned from API for the specified date range.")
        return

    # Generate the final HTML report
    report_title = f"Google Ads Campaign Spend for Week Ending {end_date.strftime('%B %d, %Y')}"
    generate_spend_html_report(df_spend, report_title, OUTPUT_PATH, start_date, end_date)


def get_week_range():
    """Calculates the start and end date for the week ending last Saturday."""
    today = datetime.date.today()
    # weekday(): Monday is 0 and Sunday is 6. Saturday is 5.
    days_since_saturday = (today.weekday() + 2) % 7
    end_date = today - datetime.timedelta(days=days_since_saturday)
    start_date = end_date - datetime.timedelta(days=6)
    return start_date, end_date


def fetch_campaign_spend(client, customer_id, start_date, end_date):
    """
    Fetches campaign spend data from Google Ads API for a given date range.

    Args:
        client: An initialized GoogleAdsClient.
        customer_id: The Google Ads customer ID.
        start_date: The start date for the report.
        end_date: The end date for the report.

    Returns:
        A pandas DataFrame with campaign spend data, or an empty DataFrame on error.
    """
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            campaign.name,
            metrics.cost_micros
        FROM campaign
        WHERE
            segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
            AND metrics.cost_micros > 0
        ORDER BY metrics.cost_micros DESC
    """
    try:
        response = ga_service.search_stream(customer_id=customer_id, query=query)
        spend_data = []
        for batch in response:
            for row in batch.results:
                spend_data.append({
                    'Campaign': row.campaign.name,
                    'Spend': row.metrics.cost_micros / 1_000_000
                })
        
        if not spend_data:
            return pd.DataFrame()

        df = pd.DataFrame(spend_data)
        # The API returns cost per day, so we need to group by campaign and sum the cost.
        df_agg = df.groupby('Campaign').sum().sort_values('Spend', ascending=False)
        return df_agg

    except GoogleAdsException as ex:
        print(
            f'Request with ID "{ex.request_id}" failed with status '
            f'"{ex.error.code().name}" and includes the following errors:',
            file=sys.stderr
        )
        for error in ex.failure.errors:
            print(f'\tError with message "{error.message}".', file=sys.stderr)
            if error.location:
                for field_path_element in error.location.field_path_elements:
                    print(f"\t\tOn field: {field_path_element.field_name}", file=sys.stderr)
        return pd.DataFrame()


def generate_spend_html_report(df, report_title, output_path, start_date, end_date):
    """Generates and saves the final HTML report file for spend data."""
    # Add a total row for the table
    df_display = df.copy()
    total_spend = df_display['Spend'].sum()
    df_display.loc['Total'] = [total_spend]

    # Format the 'Spend' column as currency
    df_display['Spend'] = df_display['Spend'].apply(lambda x: f"${x:,.2f}")
    
    table_html = df_display.to_html(classes='styled-table')
    # Add a CSS class to the total row for styling
    table_html = table_html.replace(
        '<tr>\n      <th>Total</th>',
        '<tr class="total-row">\n      <th>Total</th>'
    )

    # Format date range for the report header
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
    {table_html}
</body>
</html>
"""
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(html_template)

    print(f"Report successfully generated: {output_path}")


if __name__ == "__main__":
    main()