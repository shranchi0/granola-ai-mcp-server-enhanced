# Next Steps with Your Client ID

You have your Client ID: `379084896468-gr4sbom78hr5778avc4g0877j0iuvo97.apps.googleusercontent.com`

## Step 1: Get Your Client Secret

If you didn't save it when creating the OAuth client:
1. Go back to Google Cloud Console → Credentials
2. Click on your OAuth client (the one you just created)
3. You should see the Client Secret there
4. **Copy it immediately** - you'll need it next

If you can't see it, you'll need to create a new OAuth client (the secret is only shown once).

## Step 2: Get Refresh Token Using OAuth Playground

### Quick Method:

1. **Go to OAuth Playground**
   - Visit: https://developers.google.com/oauthplayground/

2. **Configure Playground**
   - Click the **gear icon (⚙️)** in the top right corner
   - Check the box: **"Use your own OAuth credentials"**
   - Paste your **Client ID**: `379084896468-gr4sbom78hr5778avc4g0877j0iuvo97.apps.googleusercontent.com`
   - Paste your **Client Secret** (from Step 1)
   - Click **"Close"**

3. **Select Calendar Scope**
   - In the left panel, scroll down to **"Calendar API v3"**
   - Expand it and check: `https://www.googleapis.com/auth/calendar.readonly`
   - Click **"Authorize APIs"** button at the bottom

4. **Sign In**
   - **IMPORTANT**: Sign in with the Google account that has the calendar you want to access
   - Grant permissions when prompted

5. **Exchange for Tokens**
   - After authorization, click **"Exchange authorization code for tokens"**
   - You'll see tokens appear on the right side

6. **Copy Refresh Token**
   - Look for **"Refresh_token"** in the response (it's a long string starting with `1//`)
   - Copy the entire refresh token

## Step 3: Update Claude Desktop Config

Once you have all three (Client ID, Client Secret, Refresh Token), update your config file.

