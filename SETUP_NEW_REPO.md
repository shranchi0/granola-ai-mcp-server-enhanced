# Setting Up Your Fork on GitHub

Follow these steps to create your own GitHub repository with the enhanced Granola MCP server:

## Step 1: Create a New GitHub Repository

1. Go to https://github.com/new
2. Repository name: `granola-ai-mcp-server-enhanced` (or your preferred name)
3. Description: "Enhanced Granola MCP Server with date parsing and Google Calendar integration"
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 2: Update Remote and Push

After creating the repository, run these commands:

```bash
cd /Users/shrikolanukuduru/Desktop/granola-ai-mcp-server

# Remove the old remote
git remote remove origin

# Add your new repository as the remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/granola-ai-mcp-server-enhanced.git

# Push your enhanced code
git push -u origin main
```

## Step 3: Update README (Optional)

If you want to update the repository URL in the README, edit it to point to your new repository.

## Alternative: Using GitHub CLI

If you have GitHub CLI installed:

```bash
cd /Users/shrikolanukuduru/Desktop/granola-ai-mcp-server

# Remove old remote
git remote remove origin

# Create repo and push (replace YOUR_USERNAME)
gh repo create YOUR_USERNAME/granola-ai-mcp-server-enhanced --public --source=. --remote=origin --push
```

## What's Been Committed

Your repository now includes:
- ✅ Enhanced server.py with date parsing and Google Calendar integration
- ✅ Updated pyproject.toml with Google Calendar dependencies
- ✅ Enhanced README.md documenting all new features
- ✅ CHANGELOG.md with detailed change log
- ✅ test_mcp_server.py for testing

All changes are committed and ready to push!

