#!/usr/bin/env python3
"""Exchange authorization code for refresh token."""

from google_auth_oauthlib.flow import Flow
import os
import sys

# Get credentials from environment or command line args
if len(sys.argv) >= 3:
    CLIENT_ID = sys.argv[1]
    CLIENT_SECRET = sys.argv[2]
    redirect_url = sys.argv[3] if len(sys.argv) > 3 else None
else:
    CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID') or input("Enter your Google Client ID: ").strip()
    CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET') or input("Enter your Google Client Secret: ").strip()
    redirect_url = input("Paste the redirect URL from your browser: ").strip().strip('"').strip("'")

REDIRECT_URI = 'http://localhost:8080/'

# Allow HTTP for localhost
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

flow = Flow.from_client_config(
    {
        'web': {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [REDIRECT_URI]
        }
    },
    scopes=['https://www.googleapis.com/auth/calendar.readonly'],
    redirect_uri=REDIRECT_URI
)

try:
    flow.fetch_token(authorization_response=redirect_url)
    creds = flow.credentials
    
    print('\n' + '='*60)
    print('SUCCESS! Here are your credentials for Claude Desktop config:')
    print('='*60)
    print(f'\n"GOOGLE_CLIENT_ID": "{CLIENT_ID}"')
    print(f'"GOOGLE_CLIENT_SECRET": "{CLIENT_SECRET}"')
    print(f'"GOOGLE_REFRESH_TOKEN": "{creds.refresh_token}"')
    print('\n' + '='*60)
except Exception as e:
    print(f'\nError: {e}')
    import traceback
    traceback.print_exc()

