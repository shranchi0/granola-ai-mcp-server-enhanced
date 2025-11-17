# Changelog

## Enhanced Version (Fork)

### Added
- **Date-Aware Search**: Natural language date queries ("this week", "last week", "November 2025", "today", "yesterday")
- **Google Calendar Integration**: Fetch upcoming scheduled meetings from Google Calendar
- **Unified Meeting View**: See both past meetings (Granola) and upcoming meetings (Calendar) together
- **Visual Indicators**: Calendar events marked with 📅, Granola meetings with 🎙️
- **Smart Fallbacks**: Shows recent meetings when no matches found for date ranges
- **Better Organization**: Separates past and upcoming meetings in results

### Enhanced
- **Search Results**: Improved chronological sorting and organization
- **Date Parsing**: Intelligent timezone-aware date range detection
- **Error Handling**: Better handling of missing calendar credentials

### Changed
- **Dependencies**: Added `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`
- **Configuration**: Added optional Google Calendar credentials via environment variables

## Original Version

See [proofgeist/granola-ai-mcp-server](https://github.com/proofgeist/granola-ai-mcp-server) for original features and changelog.

