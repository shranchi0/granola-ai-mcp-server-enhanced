# Granola MCP Server (Enhanced)

An enhanced Model Context Protocol (MCP) server that brings your Granola.ai meeting history and Google Calendar together in Claude Desktop. Search meetings with natural language, access transcripts, and see both past and upcoming meetings in one unified view.

> **Note**: Based on [proofgeist/granola-ai-mcp-server](https://github.com/proofgeist/granola-ai-mcp-server) with significant enhancements.

## ✨ Features

- **🗓️ Intelligent Date Search** - Natural language queries like "this week", "last week", "November 2025"
- **📅 Google Calendar Integration** - Unified view of past meetings and upcoming events
- **🔍 Smart Category Search** - Find companies by industry (devtools, fintech, AI/ML, etc.) with pre-classified tags
- **⚡ Fast Performance** - Background classification for instant category searches
- **🌍 Timezone-Aware** - All timestamps display in your local timezone
- **🔒 Privacy-First** - 100% local processing, no data sent to third parties

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- macOS with Granola.ai installed
- Claude Desktop application

### Installation

1. **Clone and install:**
   ```bash
   git clone https://github.com/shranchi0/granola-ai-mcp-server-enhanced.git
   cd granola-ai-mcp-server-enhanced
   uv sync
   ```

2. **Configure Claude Desktop:**
   
   Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
   
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

3. **Restart Claude Desktop** and test: *"tell me about my meetings this week"*

### Google Calendar Setup (Optional)

**Easy Setup:**
```bash
uv run python setup_google_calendar.py
```

This interactive script guides you through the entire process and can automatically update your Claude Desktop config.

**Manual Setup:** See [SETUP_GCal.md](SETUP_GCal.md)

> **👥 For Teams**: See [TEAM_SETUP.md](TEAM_SETUP.md) - each person needs their own Google Calendar credentials.

## 💬 Usage Examples

### Date Queries
- *"Tell me about my meetings this week"*
- *"Show me meetings from last week"*
- *"What meetings do I have today?"*
- *"Find meetings in November 2025"*
- *"Who did I meet on Friday last week?"*

### Category Search
- *"What devtools companies have I met?"*
- *"Show me fintech companies from last month"*
- *"What AI/ML companies have I met?"*

### Search & Discovery
- *"Search for meetings about quarterly planning"*
- *"Find meetings with David"*
- *"Show me team meetings"*

### Transcripts & Details
- *"Get the transcript from yesterday's meeting"*
- *"What was discussed in the planning meeting?"*
- *"Show me details about meeting [ID]"*

## 🛠️ Available Tools

| Tool | Description |
|------|-------------|
| `search_meetings` | Search with natural language date queries or keywords |
| `search_companies_by_category` | Find companies by industry/category (devtools, fintech, etc.) |
| `find_similar_companies` | Semantic search for similar companies using team-wide database |
| `get_meeting_details` | Get comprehensive meeting metadata |
| `get_meeting_transcript` | Retrieve full meeting transcripts |
| `get_meeting_documents` | Access meeting notes and documents |
| `analyze_meeting_patterns` | Analyze patterns (participants, frequency, topics) |

## 🔧 Configuration

### Environment Variables (Optional)

Add to `env` section in Claude Desktop config:

```json
"env": {
  "GOOGLE_CLIENT_ID": "your-client-id",
  "GOOGLE_CLIENT_SECRET": "your-client-secret",
  "GOOGLE_REFRESH_TOKEN": "your-refresh-token",
  "OPENAI_API_KEY": "your-openai-key",
  "TURBOPUFFER_API_KEY": "your-turbopuffer-key",
  "TURBOPUFFER_NAMESPACE": "granola-meetings"
}
```

- **Google Calendar**: See [SETUP_GCal.md](SETUP_GCal.md)
- **OpenAI API**: Required for intelligent category search
- **Turbopuffer**: Optional, enables team-wide semantic search

### File Locations

- **Claude Desktop Config**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Granola Cache**: `~/Library/Application Support/Granola/cache-v3.json`
- **Classification Cache**: `~/Library/Application Support/Granola/meeting-classifications.json`

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Cache file not found | Ensure Granola.ai is installed and has processed meetings |
| `uv` command not found | Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Server not appearing | Verify absolute path in config and restart Claude Desktop |
| Google Calendar not working | Check credentials in `env` section, verify API is enabled |
| Searches are slow | First category search triggers background classification (30-60s), subsequent searches are instant |

## 🔒 Security & Privacy

- ✅ **100% Local Processing** - Granola data never leaves your machine
- ✅ **OAuth 2.0** - Google Calendar uses secure token-based auth
- ✅ **Read-Only Access** - No modifications to your data
- ✅ **No Data Storage** - Nothing sent to third parties (except OpenAI/Turbopuffer if configured)

## 📊 Performance

- ⚡ **Fast**: Sub-2 second loading for 300+ meetings
- 🏷️ **Pre-Classified**: Background classification for instant category searches
- 🔍 **Efficient**: Tag-based search with GPT fallback for new meetings
- 🌍 **Timezone Smart**: Automatic local timezone detection

## 📚 Additional Documentation

- **[TEAM_SETUP.md](TEAM_SETUP.md)** - Team onboarding guide
- **[SETUP_GCal.md](SETUP_GCal.md)** - Google Calendar setup (step-by-step)
- **[TEAM_GOOGLE_SETUP.md](TEAM_GOOGLE_SETUP.md)** - Simplified team Google Calendar setup

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Credits

Based on [proofgeist/granola-ai-mcp-server](https://github.com/proofgeist/granola-ai-mcp-server) with enhancements:
- Intelligent date parsing and timezone handling
- Google Calendar integration
- Background classification for instant category search
- Team-wide semantic search with Turbopuffer
- Enhanced search capabilities
