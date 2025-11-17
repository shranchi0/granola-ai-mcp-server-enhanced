# Granola MCP Server (Enhanced)

An enhanced Model Context Protocol (MCP) server that brings your Granola.ai meeting history and Google Calendar together in Claude Desktop. Search meetings with natural language, access transcripts, and see both past and upcoming meetings in one unified view.

> **Note**: Based on [proofgeist/granola-ai-mcp-server](https://github.com/proofgeist/granola-ai-mcp-server) with significant enhancements.

## ✨ Key Features

### 🗓️ Intelligent Date Search
- **Natural language queries**: "this week", "last week", "November 2025", "today", "yesterday"
- **Smart date parsing**: Automatically understands and filters by date ranges
- **Timezone-aware**: All timestamps display in your local timezone

### 📅 Google Calendar Integration
- **Unified view**: See past meetings (Granola) and upcoming events (Calendar) together
- **Automatic sync**: Calendar events appear when querying "this week" or date ranges
- **Visual indicators**: 📅 for Calendar events, 🎙️ for Granola meetings

### 🔍 Enhanced Search
- **Multi-field search**: Titles, participants, transcripts, and content
- **Smart organization**: Separates past vs upcoming, sorted chronologically
- **Fallback handling**: Shows recent meetings when no matches found

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- macOS with Granola.ai installed
- Claude Desktop application
- (Optional) Google Calendar API credentials

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shranchi0/granola-ai-mcp-server-enhanced.git
   cd granola-ai-mcp-server-enhanced
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Configure Claude Desktop:**
   
   Edit `claude_desktop_config.json` (see [config locations](#configuration)):
   
   ```json
   {
     "mcpServers": {
       "granola": {
         "command": "uv",
         "args": [
           "--directory",
           "/absolute/path/to/granola-ai-mcp-server-enhanced",
           "run",
           "granola-mcp-server"
         ],
         "env": {}
       }
     }
   }
   ```
   
   Replace `/absolute/path/to/granola-ai-mcp-server-enhanced` with your actual path.

4. **Restart Claude Desktop**

5. **Test it:**
   Ask Claude: *"tell me about my meetings this week"*

### Google Calendar Setup (Optional)

**Easy Setup (Recommended):**
```bash
uv run python setup_google_calendar.py
```

This interactive script guides you through the entire process step-by-step and can automatically update your Claude Desktop config.

**Manual Setup:**
1. Follow the detailed guide: [SETUP_GCal.md](SETUP_GCal.md)
2. Or use the helper script: `uv run python get_refresh_token.py`

> **👥 For Teams**: See [TEAM_SETUP.md](TEAM_SETUP.md) for team onboarding. Each person needs their own Google Calendar credentials.

## 💬 Usage Examples

Once configured, use natural language queries in Claude Desktop:

### Date Queries
- *"Tell me about my meetings this week"*
- *"Show me meetings from last week"*
- *"What meetings do I have today?"*
- *"Find meetings in November 2025"*

### Search & Discovery
- *"Search for meetings about quarterly planning"*
- *"Find meetings with David"*
- *"Show me team meetings"*

### Transcripts & Details
- *"Get the transcript from yesterday's meeting"*
- *"What was discussed in the planning meeting?"*
- *"Show me details about meeting [ID]"*

### Analysis
- *"Analyze participant patterns from last month"*
- *"What documents are associated with the product review meeting?"*

## 🛠️ Available Tools

| Tool | Description |
|------|-------------|
| `search_meetings` | Search with natural language date queries or keywords |
| `get_meeting_details` | Get comprehensive meeting metadata |
| `get_meeting_transcript` | Retrieve full meeting transcripts |
| `get_meeting_documents` | Access meeting notes and documents |
| `analyze_meeting_patterns` | Analyze patterns (participants, frequency, topics) |

See the [full tool documentation](#available-tools) below for details.

## 📋 Configuration

### Claude Desktop Config Locations
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Granola Cache Location
- **macOS**: `~/Library/Application Support/Granola/cache-v3.json`

## 🔧 Development

```bash
# Run tests
uv run python test_server.py

# Run server directly
uv run granola-mcp-server

# Add dependencies
uv add package-name
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Cache file not found | Ensure Granola.ai is installed and has processed meetings |
| `uv` command not found | Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Server not appearing | Verify absolute path in config and restart Claude Desktop |
| Google Calendar not working | Check credentials in `env` section, verify API is enabled |
| Permission denied | Ensure cache file is readable: `chmod 644 ~/Library/Application\ Support/Granola/cache-v3.json` |

## 🔒 Security & Privacy

- ✅ **100% Local Processing** - Granola data never leaves your machine
- ✅ **OAuth 2.0** - Google Calendar uses secure token-based auth
- ✅ **Read-Only Access** - No modifications to your data
- ✅ **No Data Storage** - Nothing sent to third parties

## 📊 Performance

- ⚡ **Fast**: Sub-2 second loading for 300+ meetings
- 📝 **Rich Content**: 25,000+ character transcripts
- 🔍 **Efficient**: Multi-field search across all meeting data
- 🌍 **Timezone Smart**: Automatic local timezone detection

## 📚 Documentation

- **[TEAM_SETUP.md](TEAM_SETUP.md)** - Team onboarding guide
- **[SETUP_GCal.md](SETUP_GCal.md)** - Google Calendar setup (step-by-step)
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Credits

Based on [proofgeist/granola-ai-mcp-server](https://github.com/proofgeist/granola-ai-mcp-server) with enhancements:
- Intelligent date parsing and timezone handling
- Google Calendar integration
- Unified meeting view
- Enhanced search capabilities

---

## 📖 Detailed Tool Documentation

### search_meetings

Search meetings with natural language or keywords.

**Parameters:**
- `query` (string): Search query - supports date queries like "this week", "last week", "November 2025", or keywords
- `limit` (integer, optional): Maximum results (default: 10)

**Date Query Examples:**
- `"this week"` → Monday to Sunday of current week
- `"last week"` → Previous week
- `"November 2025"` → All meetings in November 2025
- `"today"` / `"yesterday"` → Specific days

### get_meeting_details

Get comprehensive information about a specific meeting.

**Parameters:**
- `meeting_id` (string): Meeting ID from search results

### get_meeting_transcript

Retrieve the full transcript with speaker identification.

**Parameters:**
- `meeting_id` (string): Meeting ID from search results

### get_meeting_documents

Access meeting notes, summaries, and documents.

**Parameters:**
- `meeting_id` (string): Meeting ID from search results

### analyze_meeting_patterns

Analyze patterns across multiple meetings.

**Parameters:**
- `pattern_type` (string): `"topics"`, `"participants"`, or `"frequency"`
- `date_range` (object, optional): `{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}`
