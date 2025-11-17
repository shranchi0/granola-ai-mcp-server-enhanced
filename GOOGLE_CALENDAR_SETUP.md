# Google Calendar Setup Guide

The current Google OAuth credentials appear to be invalid (deleted client). Here's how to set up new credentials:

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Google Calendar API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

## Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (unless you have a Google Workspace)
   - Fill in required fields (App name, User support email, Developer contact)
   - Add scopes: `https://www.googleapis.com/auth/calendar.readonly`
   - Add test users (your email) if needed
4. Create OAuth client:
   - Application type: "Desktop app"
   - Name: "Granola MCP Server" (or any name)
   - Click "Create"
5. **Save the Client ID and Client Secret** - you'll need these!

## Step 3: Get Refresh Token

You need to get a refresh token using one of these methods:

### Method 1: Using OAuth Playground (Easiest)

1. Go to [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
2. Click the gear icon (⚙️) in top right
3. Check "Use your own OAuth credentials"
4. Enter your Client ID and Client Secret
5. In the left panel, find "Calendar API v3"
6. Select `https://www.googleapis.com/auth/calendar.readonly`
7. Click "Authorize APIs"
8. **Important**: When prompted, sign in with the Google account that has access to 
   the calendar you want to use (this can be different from your Claude account)
9. Grant permissions
10. Click "Exchange authorization code for tokens"
11. **Copy the Refresh Token** - this is what you need!

**Note**: The refresh token will be tied to whichever Google account you authenticate with. 
You can use a different account than the one associated with Claude.

### Method 2: Using Python Script

Create a file `get_refresh_token.py`:

```python
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import json

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CLIENT_ID = 'YOUR_CLIENT_ID'
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
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

auth_url, _ = flow.authorization_url(prompt='consent')
print(f'Go to: {auth_url}')
print('After authorization, paste the full redirect URL here:')
redirect_response = input()

flow.fetch_token(authorization_response=redirect_response)
creds = flow.credentials

print(f'\nRefresh Token: {creds.refresh_token}')
print(f'\nAdd these to your Claude Desktop config:')
print(f'GOOGLE_CLIENT_ID: {CLIENT_ID}')
print(f'GOOGLE_CLIENT_SECRET: {CLIENT_SECRET}')
print(f'GOOGLE_REFRESH_TOKEN: {creds.refresh_token}')
```

Run it:
```bash
uv run python get_refresh_token.py
```

## Step 4: Update Claude Desktop Config

Update your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "granola": {
      "command": "/Users/shrikolanukuduru/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/shrikolanukuduru/Desktop/granola-ai-mcp-server",
        "run",
        "granola-mcp-server"
      ],
      "env": {
        "GOOGLE_CLIENT_ID": "YOUR_NEW_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET": "YOUR_NEW_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN": "YOUR_NEW_REFRESH_TOKEN"
      }
    }
  }
}
```

## Step 5: Restart Claude Desktop

After updating the config, restart Claude Desktop completely.

## Troubleshooting

**"Invalid grant" error:**
- The refresh token may have expired or been revoked
- Generate a new refresh token

**"Access denied" error:**
- Make sure you've enabled the Calendar API
- Check that the OAuth consent screen is configured
- Ensure you're using the correct scopes

**"deleted_client" error:**
- The OAuth client was deleted from Google Cloud Console
- Create a new OAuth client and get new credentials

## Security Note

⚠️ **Keep your credentials secure!** Never commit them to public repositories. Consider using environment variables or a secrets manager for production use.

