# Generates weekly reporting with a 6 week lookback ending the most recent saturday

## Get started

Save `credentials.json` in `/.env`. You can create this from the Google Cloud dashboard.

`> python3 run_all_reports` generates all the reports.

### Dependencies

The current iteration builds on a custom dimension for channels, as well as defined key events in GA4.
