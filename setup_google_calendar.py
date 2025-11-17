#!/usr/bin/env python3
"""
Interactive Google Calendar Setup Script
Guides you through the entire setup process step-by-step.
"""

import os
import sys
import webbrowser
from pathlib import Path

def print_step(step_num, title):
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {title}")
    print('='*60)

def print_info(text):
    print(f"\nℹ️  {text}")

def print_success(text):
    print(f"\n✅ {text}")

def print_warning(text):
    print(f"\n⚠️  {text}")

def get_user_input(prompt, default=None):
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    return input(f"{prompt}: ").strip()

def main():
    print("="*60)
    print("Google Calendar Setup for Granola MCP Server")
    print("="*60)
    print("\nThis script will guide you through setting up Google Calendar integration.")
    print("Estimated time: 10-15 minutes")
    
    # Step 1: Check if they have a Google Cloud project
    print_step(1, "Google Cloud Project Setup")
    print_info("You need a Google Cloud project with Calendar API enabled.")
    
    has_project = get_user_input("Do you already have a Google Cloud project? (yes/no)", "no").lower()
    
    if has_project == "no":
        print_info("Opening Google Cloud Console...")
        print_info("1. Create a new project (or select existing)")
        print_info("2. Enable Google Calendar API")
        print_info("3. Configure OAuth consent screen")
        print_info("4. Create OAuth credentials")
        
        open_console = get_user_input("\nOpen Google Cloud Console? (yes/no)", "yes").lower()
        if open_console == "yes":
            webbrowser.open("https://console.cloud.google.com/")
        
        input("\nPress Enter when you've completed the Google Cloud setup...")
    
    # Step 2: Get OAuth credentials
    print_step(2, "OAuth Credentials")
    print_info("You need Client ID and Client Secret from Google Cloud Console.")
    print_info("Find them at: APIs & Services > Credentials")
    
    client_id = get_user_input("\nEnter your Google Client ID")
    client_secret = get_user_input("Enter your Google Client Secret")
    
    # Step 3: Get refresh token
    print_step(3, "Get Refresh Token")
    print_info("We'll use OAuth Playground to get your refresh token.")
    
    print("\nOpening OAuth Playground...")
    webbrowser.open("https://developers.google.com/oauthplayground/")
    
    print("\nFollow these steps:")
    print("1. Click the gear icon (⚙️) in top right")
    print("2. Check 'Use your own OAuth credentials'")
    print(f"3. Enter Client ID: {client_id}")
    print(f"4. Enter Client Secret: {client_secret}")
    print("5. Close the settings")
    print("6. In left panel, find 'Calendar API v3'")
    print("7. Check 'https://www.googleapis.com/auth/calendar.readonly'")
    print("8. Click 'Authorize APIs'")
    print("9. Sign in with the Google account that has your calendar")
    print("10. Click 'Exchange authorization code for tokens'")
    print("11. Copy the 'Refresh_token' value")
    
    refresh_token = get_user_input("\nPaste your Refresh Token here")
    
    # Step 4: Generate config
    print_step(4, "Generate Claude Desktop Config")
    
    # Find Claude config file
    config_paths = {
        "darwin": Path.home() / "Library/Application Support/Claude/claude_desktop_config.json",
        "win32": Path(os.getenv("APPDATA")) / "Claude/claude_desktop_config.json",
        "linux": Path.home() / ".config/Claude/claude_desktop_config.json"
    }
    
    config_path = config_paths.get(sys.platform)
    if not config_path:
        config_path = Path.home() / ".config/Claude/claude_desktop_config.json"
    
    print_info(f"Claude config location: {config_path}")
    
    update_config = False
    repo_path = None
    
    if not config_path.exists():
        print_warning("Claude config file not found. You'll need to create it manually.")
        print("\nYou'll need to add the config manually (see below).")
    else:
        print_success(f"Found config file at: {config_path}")
        update_config = get_user_input("Update config file automatically? (yes/no)", "yes").lower() == "yes"
        
        if update_config:
            import json
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Get repo path
                repo_path = Path(__file__).parent.absolute()
                print_info(f"Detected repo path: {repo_path}")
                use_detected = get_user_input("Use this path? (yes/no)", "yes").lower()
                
                if use_detected != "yes":
                    repo_path = Path(get_user_input("Enter absolute path to granola-ai-mcp-server-enhanced"))
                
                # Update config
                if "mcpServers" not in config:
                    config["mcpServers"] = {}
                
                config["mcpServers"]["granola"] = {
                    "command": "uv",
                    "args": [
                        "--directory",
                        str(repo_path),
                        "run",
                        "granola-mcp-server"
                    ],
                    "env": {
                        "GOOGLE_CLIENT_ID": client_id,
                        "GOOGLE_CLIENT_SECRET": client_secret,
                        "GOOGLE_REFRESH_TOKEN": refresh_token
                    }
                }
                
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print_success("Config file updated!")
                
            except Exception as e:
                print_warning(f"Could not update config automatically: {e}")
                print("\nYou'll need to add the config manually (see below).")
                update_config = False
    
    if not update_config:
        if repo_path is None:
            repo_path = Path(__file__).parent.absolute()
            print_info(f"Using detected repo path: {repo_path}")
            use_detected = get_user_input("Use this path? (yes/no)", "yes").lower()
            if use_detected != "yes":
                repo_path = Path(get_user_input("Enter absolute path to granola-ai-mcp-server-enhanced"))
        
        import json
        print("\n" + "="*60)
        print("Add this to your claude_desktop_config.json:")
        print("="*60)
        config_json = {
            "mcpServers": {
                "granola": {
                    "command": "uv",
                    "args": [
                        "--directory",
                        str(repo_path),
                        "run",
                        "granola-mcp-server"
                    ],
                    "env": {
                        "GOOGLE_CLIENT_ID": client_id,
                        "GOOGLE_CLIENT_SECRET": client_secret,
                        "GOOGLE_REFRESH_TOKEN": refresh_token
                    }
                }
            }
        }
        print(json.dumps(config_json, indent=2))
    
    # Step 5: Final instructions
    print_step(5, "Complete Setup")
    print_success("Setup complete!")
    print("\nNext steps:")
    print("1. Restart Claude Desktop completely")
    print("2. Ask Claude: 'tell me about my meetings this week'")
    print("3. You should see both Granola meetings and Calendar events!")
    
    print("\n" + "="*60)
    print("Setup Complete! 🎉")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

