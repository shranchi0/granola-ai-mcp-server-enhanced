#!/usr/bin/env python3
"""Helper script to get Google Calendar refresh token."""

from google_auth_oauthlib.flow import Flow
import json

# Get these from Google Cloud Console
CLIENT_ID = input("Enter your Google Client ID: ").strip()
CLIENT_SECRET = input("Enter your Google Client Secret: ").strip()

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
REDIRECT_URI = 'http://localhost:8080/'

flow = Flow.from_client_config(
    {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    },
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
print(f'\n1. Open this URL in your browser:')
print(f'\n{auth_url}\n')
print('2. IMPORTANT: When prompted, sign in with the Google account that has')
print('   access to the calendar you want to use (can be different from Claude account)')
print('3. Grant permissions for calendar access')
print('4. After authorization, you\'ll be redirected to a localhost URL')
print('5. Copy the ENTIRE redirect URL (including http://localhost:8080/?code=...)')
print('   IMPORTANT: If you get a zsh error, paste the URL in quotes like this:')
print('   "http://localhost:8080/?code=..."')
print('\nPaste the full redirect URL here (you can use quotes):')
redirect_response = input().strip()
# Remove quotes if user added them
redirect_response = redirect_response.strip('"').strip("'")

try:
    flow.fetch_token(authorization_response=redirect_response)
    creds = flow.credentials
    
    print('\n' + '='*60)
    print('SUCCESS! Add these to your Claude Desktop config:')
    print('='*60)
    print(f'\n"GOOGLE_CLIENT_ID": "{CLIENT_ID}"')
    print(f'"GOOGLE_CLIENT_SECRET": "{CLIENT_SECRET}"')
    print(f'"GOOGLE_REFRESH_TOKEN": "{creds.refresh_token}"')
    print('\n' + '='*60)
except Exception as e:
    print(f'\nError: {e}')
    print('\nMake sure you:')
    print('1. Copied the ENTIRE redirect URL')
    print('2. Enabled Google Calendar API in Google Cloud Console')
    print('3. Created OAuth credentials with correct redirect URI')

