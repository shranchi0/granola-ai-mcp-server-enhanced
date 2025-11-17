# Team Setup Guide

This guide helps teams set up the Granola MCP Server for multiple users.

## Can My Team Use This?

**Yes!** Your team can use this repository, but each person needs to:

1. ✅ Clone the repository
2. ✅ Install dependencies (`uv sync`)
3. ✅ Set up their own Google Calendar credentials (if using Calendar integration)
4. ✅ Configure their own Claude Desktop config file

## What Each Team Member Needs to Do

### Step 1: Clone and Install (5 minutes)

```bash
git clone https://github.com/shranchi0/granola-ai-mcp-server-enhanced.git
cd granola-ai-mcp-server-enhanced
uv sync
```

### Step 2: Configure Claude Desktop (2 minutes)

Each person needs to update their Claude Desktop config with their own paths:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "granola": {
      "command": "uv",
      "args": [
        "--directory",
        "/YOUR/ABSOLUTE/PATH/TO/granola-ai-mcp-server-enhanced",
        "run",
        "granola-mcp-server"
      ],
      "env": {}
    }
  }
}
```

**Replace** `/YOUR/ABSOLUTE/PATH/TO/` with your actual path to the cloned repository.

### Step 3: Google Calendar (Optional - 15 minutes per person)

If team members want Google Calendar integration:

1. Each person creates their own Google Cloud project (or you can share one project)
2. Each person creates their own OAuth credentials
3. Each person gets their own refresh token
4. Each person adds their credentials to their own Claude Desktop config

**Note**: You can share a Google Cloud project, but each person still needs their own OAuth client and refresh token.

## Quick Setup Checklist

For each team member:

- [ ] Clone repository
- [ ] Run `uv sync`
- [ ] Update Claude Desktop config with correct path
- [ ] Restart Claude Desktop
- [ ] Test: "tell me about my meetings this week"
- [ ] (Optional) Set up Google Calendar credentials
- [ ] (Optional) Test Calendar integration

## Common Issues

### "Cache file not found"
- Make sure Granola.ai is installed
- Check that `~/Library/Application Support/Granola/cache-v3.json` exists

### "uv command not found"
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Or use `python` instead of `uv` in the config

### Path Issues
- Use absolute paths, not relative paths
- On macOS: `/Users/username/path/to/repo`
- On Windows: `C:\Users\username\path\to\repo`
- On Linux: `/home/username/path/to/repo`

### Google Calendar Not Working
- Each person needs their own credentials
- Follow `SETUP_GCal.md` for detailed instructions

## Sharing a Google Cloud Project (Optional)

If your team wants to share a Google Cloud project:

1. One person creates the project
2. Share project access with team members
3. Each person creates their own OAuth client in the shared project
4. Each person gets their own refresh token

This is optional - each person can also create their own project.

## Support

If team members run into issues:
1. Check the main README.md
2. Check SETUP_GCal.md for Calendar setup
3. Check troubleshooting sections in the docs

