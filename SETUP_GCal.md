# Step-by-Step Google Calendar Setup Guide

Follow these steps to set up Google Calendar access for your Granola MCP server.

## Step 1: Create Google Cloud Project

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Sign in with any Google account (doesn't have to be your calendar account)

2. **Create a New Project**
   - Click the project dropdown at the top
   - Click "New Project"
   - Name it: `Granola MCP Server` (or any name)
   - Click "Create"
   - Wait for it to be created, then select it from the dropdown

## Step 2: Enable Google Calendar API

1. **Navigate to APIs & Services**
   - In the left sidebar, click "APIs & Services" > "Library"
   - Or go directly to: https://console.cloud.google.com/apis/library

2. **Search for Calendar API**
   - In the search bar, type: `Google Calendar API`
   - Click on "Google Calendar API" from the results

3. **Enable the API**
   - Click the blue "Enable" button
   - Wait for it to enable (may take a few seconds)

## Step 3: Configure OAuth Consent Screen

1. **Go to OAuth Consent Screen**
   - In the left sidebar, click "APIs & Services" > "OAuth consent screen"
   - Or go to: https://console.cloud.google.com/apis/credentials/consent

2. **Choose User Type**
   - Select "External" (unless you have Google Workspace)
   - Click "Create"

3. **Fill in App Information**
   - **App name**: `Granola MCP Server` (or any name)
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
   - Click "Save and Continue"

4. **Add Scopes**
   - Click "Add or Remove Scopes"
   - In the filter box, search for: `calendar.readonly`
   - Check the box for: `https://www.googleapis.com/auth/calendar.readonly`
   - Click "Update"
   - Click "Save and Continue"

5. **Add Test Users** (if app is in Testing mode)
   - Click "Add Users"
   - Add the email address of the Google account that has the calendar you want to access
   - Click "Add"
   - Click "Save and Continue"

6. **Review**
   - Review the summary
   - Click "Back to Dashboard"

## Step 4: Create OAuth 2.0 Credentials

1. **Go to Credentials**
   - In the left sidebar, click "APIs & Services" > "Credentials"
   - Or go to: https://console.cloud.google.com/apis/credentials

2. **Create OAuth Client ID**
   - Click "+ Create Credentials" at the top
   - Select "OAuth client ID"

3. **Configure OAuth Client**
   - **Application type**: Select "Desktop app"
   - **Name**: `Granola MCP Desktop` (or any name)
   - Click "Create"

4. **Save Your Credentials**
   - A popup will show your **Client ID** and **Client Secret**
   - **IMPORTANT**: Copy both of these now - you won't be able to see the secret again!
   - Click "OK"

## Step 5: Get Refresh Token

You have two options - choose the easiest for you:

### Option A: Using OAuth Playground (Recommended - Easiest)

1. **Go to OAuth Playground**
   - Visit: https://developers.google.com/oauthplayground/

2. **Configure Playground**
   - Click the gear icon (⚙️) in the top right corner
   - Check the box: "Use your own OAuth credentials"
   - Paste your **Client ID** in the first field
   - Paste your **Client Secret** in the second field
   - Click "Close"

3. **Select Calendar Scope**
   - In the left panel, scroll down to "Calendar API v3"
   - Expand it and check: `https://www.googleapis.com/auth/calendar.readonly`
   - Click "Authorize APIs" button at the bottom

4. **Sign In**
   - **IMPORTANT**: Sign in with the Google account that has access to the calendar you want to use
   - This can be different from your Claude account!
   - Grant permissions when prompted

5. **Exchange for Tokens**
   - After authorization, click "Exchange authorization code for tokens"
   - You'll see tokens appear on the right side

6. **Copy Refresh Token**
   - Look for "Refresh_token" in the response
   - Copy the entire refresh token (it's a long string starting with `1//`)

### Option B: Using Python Script

1. **Run the helper script**
   ```bash
   cd /path/to/granola-ai-mcp-server
   uv run python get_refresh_token.py
   ```

2. **Follow the prompts**
   - Enter your Client ID when prompted
   - Enter your Client Secret when prompted
   - A URL will appear - open it in your browser
   - **Sign in with the Google account that has the calendar you want**
   - Grant permissions
   - Copy the redirect URL and paste it back into the script
   - The script will output your refresh token

## Step 6: Update Claude Desktop Config

1. **Open Claude Desktop Config**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Add Google Credentials**
   Update the `env` section to include your credentials. Replace paths with your actual paths:

   ```json
   {
     "mcpServers": {
       "granola": {
         "command": "uv",
         "args": [
           "--directory",
           "/absolute/path/to/granola-ai-mcp-server",
           "run",
           "granola-mcp-server"
         ],
         "env": {
           "GOOGLE_CLIENT_ID": "YOUR_CLIENT_ID_HERE",
           "GOOGLE_CLIENT_SECRET": "YOUR_CLIENT_SECRET_HERE",
           "GOOGLE_REFRESH_TOKEN": "YOUR_REFRESH_TOKEN_HERE"
         }
       }
     }
   }
   ```

3. **Replace the placeholders**
   - Replace `YOUR_CLIENT_ID_HERE` with your actual Client ID
   - Replace `YOUR_CLIENT_SECRET_HERE` with your actual Client Secret
   - Replace `YOUR_REFRESH_TOKEN_HERE` with your actual Refresh Token

4. **Save the file**

## Step 7: Restart Claude Desktop

1. **Quit Claude Desktop completely**
   - Press `Cmd + Q` or right-click the icon → Quit
   - Make sure it's fully closed

2. **Restart Claude Desktop**

3. **Test it**
   - Ask Claude: "tell me about my meetings this week"
   - You should see both Granola meetings (past) and Calendar events (upcoming)

## Troubleshooting

### "Invalid grant" error
- Your refresh token may have expired
- Generate a new refresh token using Step 5

### "Access denied" or "Permission denied"
- Make sure you enabled Google Calendar API (Step 2)
- Check that you added the correct scope (`calendar.readonly`)
- Verify you're signed in with the correct Google account

### "deleted_client" error
- Your OAuth client was deleted
- Create a new OAuth client (Step 4) and get a new refresh token (Step 5)

### Calendar events not showing
- Check that the refresh token is for the correct Google account
- Verify the account has calendar events in the date range you're querying
- Check Claude Desktop logs for any error messages

### Can't see Client Secret
- If you lost your Client Secret, you need to create a new OAuth client
- Go to Credentials → Delete the old one → Create new one

## Security Notes

⚠️ **Keep your credentials secure!**
- Never commit them to public repositories
- Don't share your Client Secret or Refresh Token
- The config file is stored locally on your machine

## Quick Reference

**Where to find things:**
- Google Cloud Console: https://console.cloud.google.com/
- OAuth Playground: https://developers.google.com/oauthplayground/
- Claude Config: `~/Library/Application Support/Claude/claude_desktop_config.json`

**What you need:**
1. ✅ Client ID (from Google Cloud Console)
2. ✅ Client Secret (from Google Cloud Console - save it immediately!)
3. ✅ Refresh Token (from OAuth Playground or script)

That's it! Once set up, your Granola MCP server will automatically fetch upcoming calendar events when you ask about "this week" or other date queries.

