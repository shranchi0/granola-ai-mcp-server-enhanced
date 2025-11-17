# Team Google Calendar Setup Guide

For teams, you can simplify setup by sharing a Google Cloud project. Each person still needs their own OAuth client and refresh token, but you can skip creating a project.

## Option 1: Shared Google Cloud Project (Recommended for Teams)

### Admin Setup (One Person)

1. **Create Google Cloud Project**
   - Go to https://console.cloud.google.com/
   - Create project: "Granola MCP Team" (or your team name)
   - Enable Google Calendar API
   - Configure OAuth consent screen
   - Add all team members as test users

2. **Share Project Access**
   - Go to IAM & Admin > IAM
   - Click "Grant Access"
   - Add team member emails
   - Role: "Editor" or "Owner"
   - Click "Save"

### Team Member Setup (Each Person)

1. **Access Shared Project**
   - Go to https://console.cloud.google.com/
   - Select the shared project from dropdown

2. **Create Your Own OAuth Client**
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Type: Desktop app
   - Name: "Your Name - Granola MCP"
   - Click "Create"
   - **Save your Client ID and Secret**

3. **Get Refresh Token**
   - Run: `uv run python setup_google_calendar.py`
   - Or follow [SETUP_GCal.md](SETUP_GCal.md) Step 5

4. **Update Claude Desktop Config**
   - The setup script can do this automatically
   - Or add credentials manually to your config

## Option 2: Individual Projects (More Privacy)

Each person creates their own Google Cloud project. Follow [SETUP_GCal.md](SETUP_GCal.md) individually.

## Quick Comparison

| Setup Type | Time per Person | Privacy | Complexity |
|------------|----------------|--------|------------|
| Shared Project | ~5 min | Lower | Easy |
| Individual Project | ~15 min | Higher | Medium |

## Using the Interactive Setup Script

The easiest way for anyone:

```bash
cd granola-ai-mcp-server-enhanced
uv run python setup_google_calendar.py
```

The script will:
- ✅ Guide you through each step
- ✅ Open browser windows automatically
- ✅ Help you get credentials
- ✅ Update your Claude Desktop config automatically
- ✅ Verify everything is set up correctly

## Troubleshooting

**"I don't see the shared project"**
- Make sure admin added you to IAM
- Check you're signed into correct Google account
- Refresh the Google Cloud Console

**"OAuth client creation failed"**
- Make sure you're in the shared project
- Verify Calendar API is enabled
- Check OAuth consent screen is configured

**"Refresh token not working"**
- Make sure you signed in with the correct Google account
- Verify the account has access to the calendar you want
- Try generating a new refresh token

