# Reporting Automation

This project generates weekly marketing reports with data from Google Analytics and Google Ads. Most reports cover a 6-week lookback period, ending on the most recent Saturday.

## Get started

To run the reports, you first need to set up your API credentials in the `.env/` directory.

### 1. Google Analytics (GA4) Setup

The scripts for `overview`, `campaign`, `landing_page`, and `formfills` use Google Analytics data.

- Create a **Service Account** in your Google Cloud project and download its JSON key file.
- Save this file as `credentials.json` inside the `.env/` directory.

### 2. Google Ads Setup

The `paid_efficiency.py` script uses the Google Ads API.

- Create a `google-ads.yaml` file inside the `.env/` directory.
- Fill this file with your **Developer Token**, OAuth2 **Client ID**, **Client Secret**, **Refresh Token**, and the **Customer ID** of the Ads account you want to report on.

### 3. Running the Reports

Once your credentials are in place, you can run any report script individually. For example:

`> python3 overview.py`
`> python3 paid_efficiency.py`

### Dependencies

The Google Analytics reports rely on a custom dimension for channels (`sessionCustomChannelGroup`) and pre-defined key events in your GA4 property.
