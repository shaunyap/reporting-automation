#!/usr/bin/env python
#
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
 
"""Generates a refresh token for the Google Ads API.
 
This utility will help you generate a refresh token for the Google Ads API.
It will attempt to use the `client_id` and `client_secret` from your
`google-ads.yaml` file, but you can override them with command-line flags.
"""
 
import argparse
import os
import sys
import yaml
 
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
 
# The path to the google-ads.yaml file.
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '.env', 'google-ads.yaml')
 
# The scope for the Google Ads API.
GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
 
# The redirect URI for an installed application.
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
 
 
def main(client_id, client_secret, scopes):
    """Initiates the OAuth 2.0 flow to retrieve a refresh token."""
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token",
            }
        },
        scopes=scopes,
    )
    flow.redirect_uri = REDIRECT_URI
 
    # Create an authorization URL.
    auth_url, _ = flow.authorization_url(prompt="consent")
 
    print(f"Please log in to your Google Ads account and grant permissions to this application by visiting the following URL:\n\n{auth_url}\n")
 
    # Prompt the user for the authorization code.
    code = input("Enter the authorization code here: ").strip()
 
    # Exchange the authorization code for a refresh token.
    try:
        flow.fetch_token(code=code)
    except InvalidGrantError as ex:
        print(f"Authentication failed: {ex}", file=sys.stderr)
        sys.exit(1)
 
    credentials = flow.credentials
    print("\nAuthorization successful!")
    print(f"Your refresh token is: {credentials.refresh_token}")
    print("\nCopy this token and paste it into your 'google-ads.yaml' file under the 'refresh_token' key.")
 
 
if __name__ == '__main__':
    # Set up argument parser.
    parser = argparse.ArgumentParser(
        description="Generates a refresh token for the Google Ads API."
    )
    parser.add_argument(
        "--client_id",
        type=str,
        help="Your Google Ads API client ID. If not specified, the script will try to load it from google-ads.yaml.",
    )
    parser.add_argument(
        "--client_secret",
        type=str,
        help="Your Google Ads API client secret. If not specified, the script will try to load it from google-ads.yaml.",
    )
    parser.add_argument(
        "--additional_scopes",
        type=str,
        help="Additional OAuth scopes to request, separated by commas.",
    )
    args = parser.parse_args()
 
    # Load credentials from YAML if not provided via command line.
    client_id = args.client_id
    client_secret = args.client_secret
 
    if not all([client_id, client_secret]):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            if not client_id:
                client_id = config.get("client_id")
            if not client_secret:
                client_secret = config.get("client_secret")
        except FileNotFoundError:
            print(
                f"Warning: Configuration file not found at '{CONFIG_PATH}'. "
                "Please provide --client_id and --client_secret.",
                file=sys.stderr,
            )
 
    if not all([client_id, client_secret]):
        print(
            "Error: A client_id and client_secret are required. "
            "Please provide them in your 'google-ads.yaml' file or as command-line arguments.",
            file=sys.stderr,
        )
        sys.exit(1)
 
    # Configure scopes.
    configured_scopes = [GOOGLE_ADS_SCOPE]
    if args.additional_scopes:
        configured_scopes.extend(args.additional_scopes.replace(" ", "").split(","))
 
    main(client_id, client_secret, configured_scopes)