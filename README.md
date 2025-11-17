# Granola MCP Server (Enhanced)

An enhanced Model Context Protocol (MCP) server for integrating Granola.ai meeting intelligence with Claude Desktop. This fork adds intelligent date parsing, Google Calendar integration, and improved meeting search capabilities.

**Forked from:** [proofgeist/granola-ai-mcp-server](https://github.com/proofgeist/granola-ai-mcp-server)

## 🆕 Enhanced Features

### Date-Aware Search
- **Natural Language Date Queries**: Understand queries like "this week", "last week", "November 2025", "today", "yesterday"
- **Smart Date Parsing**: Automatically detects and filters meetings by date ranges
- **Timezone Intelligence**: All timestamps display in your local timezone

### Google Calendar Integration
- **Unified Meeting View**: See both past meetings (from Granola) and upcoming scheduled meetings (from Google Calendar) in one place
- **Upcoming Meetings**: Automatically fetches scheduled calendar events for "this week" queries
- **Seamless Integration**: Calendar events are marked with 📅 icon, Granola meetings with 🎙️ icon

### Enhanced Search Results
- **Past vs Upcoming**: Automatically separates past and upcoming meetings in "this week" queries
- **Fallback to Recent**: If no meetings found for a date range, shows recent meetings instead
- **Better Organization**: Results are sorted chronologically (upcoming earliest first, past most recent first)

## Features

- **Meeting Search**: Search meetings by title, content, participants, and transcript content
- **Date-Aware Search**: Natural language date queries ("this week", "last week", etc.)
- **Google Calendar Integration**: See upcoming scheduled meetings alongside past recorded meetings
- **Meeting Details**: Get comprehensive meeting metadata with local timezone display
- **Full Transcript Access**: Retrieve complete meeting conversations with speaker identification
- **Rich Document Content**: Access actual meeting notes, summaries, and structured content
- **Pattern Analysis**: Analyze patterns across meetings (participants, frequency, topics)
- **Timezone Intelligence**: All timestamps automatically display in your local timezone
- **Real-time Integration**: Seamlessly connects to your actual Granola meeting data

## Quick Start

> **👥 For Teams**: See [TEAM_SETUP.md](TEAM_SETUP.md) for team setup instructions. Each person needs their own Google Calendar credentials.

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- macOS with Granola.ai installed
- Claude Desktop application
- Granola cache file at `~/Library/Application Support/Granola/cache-v3.json`
- (Optional) Google Calendar API credentials for upcoming meetings

### Installation

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd granola-ai-mcp-server
   ```

2. **Install dependencies with uv:**
   ```bash
   uv sync
   ```

3. **Test the installation:**
   ```bash
   uv run python test_server.py
   ```

4. **Configure Claude Desktop** by adding to your `claude_desktop_config.json`:

   **Basic Configuration (Granola only):**
   ```json
   {
     "mcpServers": {
       "granola": {
         "command": "uv",
         "args": ["--directory", "/absolute/path/to/granola-ai-mcp-server", "run", "granola-mcp-server"],
         "env": {}
       }
     }
   }
   ```

   **Enhanced Configuration (with Google Calendar):**
   ```json
   {
     "mcpServers": {
       "granola": {
         "command": "uv",
         "args": ["--directory", "/absolute/path/to/granola-ai-mcp-server", "run", "granola-mcp-server"],
         "env": {
           "GOOGLE_CLIENT_ID": "your-google-client-id",
           "GOOGLE_CLIENT_SECRET": "your-google-client-secret",
           "GOOGLE_REFRESH_TOKEN": "your-google-refresh-token"
         }
       }
     }
   }
   ```
   
   **Important:** Replace `/absolute/path/to/granola-ai-mcp-server` with your actual project path.

5. **Restart Claude Desktop** to load the MCP server

### Setting Up Google Calendar Integration

**Important for Teams**: Each team member needs to set up their own Google Calendar credentials. Credentials cannot be shared between users.

To enable Google Calendar integration for upcoming meetings:

1. **Create a Google Cloud Project** and enable the Calendar API
2. **Create OAuth 2.0 credentials** (Client ID and Client Secret)
3. **Get a refresh token** using the OAuth flow
4. **Add credentials to Claude Desktop config** as shown above

The server will automatically use Google Calendar if credentials are provided, otherwise it will work with Granola data only.

## Available Tools

### search_meetings
Search meetings by query string with intelligent date parsing.

**Parameters:**
- `query` (string): Search query for meetings (supports date queries like "this week", "last week", "November 2025")
- `limit` (integer, optional): Maximum number of results (default: 10)

**Examples:**
- "this week" - Shows meetings from Monday to Sunday of current week
- "last week" - Shows meetings from previous week
- "November 2025" - Shows all meetings in November 2025
- "today" / "yesterday" - Shows meetings for specific days

### get_meeting_details
Get detailed information about a specific meeting.

**Parameters:**
- `meeting_id` (string): Meeting ID to retrieve details for

### get_meeting_transcript
Get transcript for a specific meeting.

**Parameters:**
- `meeting_id` (string): Meeting ID to get transcript for

### get_meeting_documents
Get documents associated with a meeting.

**Parameters:**
- `meeting_id` (string): Meeting ID to get documents for

### analyze_meeting_patterns
Analyze patterns across multiple meetings.

**Parameters:**
- `pattern_type` (string): Type of pattern to analyze ('topics', 'participants', 'frequency')
- `date_range` (object, optional): Date range for analysis with start_date and end_date

## Usage Examples

Once configured with Claude Desktop, you can use natural language to interact with your meetings:

### Date-Based Queries
- "Tell me about my meetings this week"
- "Show me meetings from last week"
- "Find meetings in November 2025"
- "What meetings do I have today?"
- "Show me yesterday's meetings"

### Basic Queries
- "Search for meetings about quarterly planning"
- "Find meetings with David"
- "Show me team meetings"

### Transcript Access
- "Get the transcript from yesterday's meeting"
- "What was discussed in the planning meeting?"
- "Show me the full conversation from the standup"

### Content Analysis
- "Analyze participant patterns from last month"
- "What documents are associated with the product review meeting?"
- "Search for mentions of 'schema labeling' in meeting transcripts"

## What's New in This Fork

### Enhanced Date Parsing
- Natural language date queries ("this week", "last week", month names, years)
- Automatic timezone handling
- Smart date range detection

### Google Calendar Integration
- Fetch upcoming scheduled meetings from Google Calendar
- Unified view of past (Granola) and upcoming (Calendar) meetings
- Automatic integration when credentials are provided

### Improved Search Results
- Separates past and upcoming meetings
- Shows source (Granola vs Calendar) with icons
- Fallback to recent meetings when no matches found
- Better chronological sorting

## Development

### Running Tests
```bash
uv run python test_server.py
```

### Running the Server Directly
```bash
uv run granola-mcp-server
```

### Adding Dependencies
```bash
uv add package-name
```

## Configuration

### Claude Desktop Config Locations
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Granola Cache Location
The server reads from Granola's cache file at:
```
~/Library/Application Support/Granola/cache-v3.json
```

## Security & Privacy

- ✅ **100% Local Processing** - All Granola data stays on your machine
- ✅ **Google Calendar API** - Uses OAuth 2.0 with refresh tokens (credentials stored locally)
- ✅ **Read-Only Access** - Server only reads from Granola's cache and Google Calendar
- ✅ **No Data Storage** - No meeting data is stored or transmitted to third parties

## Performance & Capabilities

- **Fast Loading**: Sub-2 second cache loading for hundreds of meetings
- **Rich Content**: Extracts 25,000+ character transcripts and meeting notes
- **Efficient Search**: Multi-field search across titles, content, participants, and transcripts
- **Memory Optimized**: Lazy loading with intelligent content parsing
- **Timezone Smart**: Automatic local timezone detection and display
- **Production Ready**: Successfully processes real Granola data (11.7MB+ cache files)
- **Scalable**: Handles large datasets with 500+ transcript segments per meeting

## Troubleshooting

### Common Issues

**"Cache file not found"**
- Ensure Granola.ai is installed and has processed some meetings
- Check that the cache file exists: `ls -la "~/Library/Application Support/Granola/cache-v3.json"`

**"uv command not found"**
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Or use pip fallback in Claude config: `"command": "python"`

**"Permission denied"**
- Ensure the cache file is readable: `chmod 644 "~/Library/Application Support/Granola/cache-v3.json"`

**Server not appearing in Claude Desktop**
- Verify the absolute path in your Claude config
- Check Claude Desktop logs for MCP server errors
- Restart Claude Desktop after config changes

**Google Calendar not working**
- Verify credentials are correctly set in environment variables
- Check that Google Calendar API is enabled in your Google Cloud project
- Ensure refresh token is valid and not expired

## License

MIT License (same as original)

## Credits

- Original work by [proofgeist](https://github.com/proofgeist/granola-ai-mcp-server)
- Enhanced with date parsing and Google Calendar integration
