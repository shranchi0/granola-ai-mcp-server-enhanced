"""Granola MCP Server implementation."""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import zoneinfo
import time
import re

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    TextContent,
    Tool,
)

from .models import CacheData, MeetingMetadata, MeetingDocument, MeetingTranscript

# Google Calendar imports (optional - only if credentials are provided)
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False
    Request = None


class GranolaMCPServer:
    """Granola MCP Server for meeting intelligence queries."""
    
    def __init__(self, cache_path: Optional[str] = None, timezone: Optional[str] = None,
                 google_client_id: Optional[str] = None,
                 google_client_secret: Optional[str] = None,
                 google_refresh_token: Optional[str] = None):
        """Initialize the Granola MCP server."""
        if cache_path is None:
            cache_path = os.path.expanduser("~/Library/Application Support/Granola/cache-v3.json")
        
        self.cache_path = cache_path
        self.server = Server("granola-mcp-server")
        self.cache_data: Optional[CacheData] = None
        
        # Set up timezone handling
        if timezone:
            self.local_timezone = zoneinfo.ZoneInfo(timezone)
        else:
            # Auto-detect local timezone
            self.local_timezone = self._detect_local_timezone()
        
        # Google Calendar credentials (from environment or parameters)
        self.google_client_id = google_client_id or os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = google_client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        self.google_refresh_token = google_refresh_token or os.getenv("GOOGLE_REFRESH_TOKEN")
        self.google_calendar_enabled = (
            GOOGLE_CALENDAR_AVAILABLE and 
            self.google_client_id and 
            self.google_client_secret and 
            self.google_refresh_token
        )
            
        self._setup_handlers()
    
    def _detect_local_timezone(self):
        """Detect the local timezone."""
        try:
            # Try to get system timezone
            if hasattr(time, 'tzname') and time.tzname:
                # Convert system timezone to zoneinfo
                # Common mappings for US timezones
                tz_mapping = {
                    'EST': 'America/New_York',
                    'EDT': 'America/New_York', 
                    'CST': 'America/Chicago',
                    'CDT': 'America/Chicago',
                    'MST': 'America/Denver',
                    'MDT': 'America/Denver',
                    'PST': 'America/Los_Angeles',
                    'PDT': 'America/Los_Angeles'
                }
                
                current_tz = time.tzname[time.daylight]
                if current_tz in tz_mapping:
                    return zoneinfo.ZoneInfo(tz_mapping[current_tz])
            
            # Fallback: try to detect from system offset
            local_offset = time.timezone if not time.daylight else time.altzone
            hours_offset = -local_offset // 3600
            
            # Common US timezone mappings by offset
            offset_mapping = {
                -8: 'America/Los_Angeles',  # PST
                -7: 'America/Denver',       # MST
                -6: 'America/Chicago',      # CST
                -5: 'America/New_York',     # EST
                -4: 'America/New_York'      # EDT (during daylight saving)
            }
            
            if hours_offset in offset_mapping:
                return zoneinfo.ZoneInfo(offset_mapping[hours_offset])
                
        except Exception as e:
            sys.stderr.write(f"Error detecting timezone: {e}\n")
        
        # Ultimate fallback to Eastern Time (common for US business)
        return zoneinfo.ZoneInfo('America/New_York')
    
    def _get_google_credentials(self) -> Optional[Credentials]:
        """Get Google Calendar credentials."""
        if not self.google_calendar_enabled:
            return None
        
        try:
            creds = Credentials(
                token=None,
                refresh_token=self.google_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.google_client_id,
                client_secret=self.google_client_secret
            )
            # Refresh the token
            creds.refresh(Request())
            return creds
        except Exception as e:
            error_msg = str(e)
            if 'deleted_client' in error_msg:
                sys.stderr.write(f"Error: Google OAuth client was deleted. Please set up new credentials.\n")
                sys.stderr.write(f"See GOOGLE_CALENDAR_SETUP.md for instructions.\n")
            else:
                sys.stderr.write(f"Error getting Google credentials: {e}\n")
            return None
    
    async def _fetch_calendar_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch calendar events from Google Calendar."""
        if not self.google_calendar_enabled:
            return []
        
        try:
            creds = self._get_google_credentials()
            if not creds:
                return []
            
            service = build('calendar', 'v3', credentials=creds)
            
            # Convert to RFC3339 format
            time_min = start_date.isoformat() + 'Z' if start_date.tzinfo is None else start_date.isoformat()
            time_max = end_date.isoformat() + 'Z' if end_date.tzinfo is None else end_date.isoformat()
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Convert to our format
            calendar_meetings = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                # Parse the datetime
                if 'T' in start:
                    event_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
                else:
                    event_date = datetime.fromisoformat(start)
                
                # Extract attendees
                attendees = []
                if 'attendees' in event:
                    attendees = [att.get('email', '') for att in event.get('attendees', [])]
                
                calendar_meetings.append({
                    'title': event.get('summary', 'No Title'),
                    'date': event_date,
                    'participants': attendees,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'id': event.get('id', ''),
                    'source': 'google_calendar'
                })
            
            return calendar_meetings
        except Exception as e:
            sys.stderr.write(f"Error fetching calendar events: {e}\n")
            return []
    
    def _convert_to_local_time(self, utc_datetime: datetime) -> datetime:
        """Convert UTC datetime to local timezone."""
        if utc_datetime.tzinfo is None:
            # Assume UTC if no timezone info
            utc_datetime = utc_datetime.replace(tzinfo=zoneinfo.ZoneInfo('UTC'))
        
        return utc_datetime.astimezone(self.local_timezone)
    
    def _format_local_time(self, utc_datetime: datetime) -> str:
        """Format datetime in local timezone for display."""
        local_dt = self._convert_to_local_time(utc_datetime)
        return local_dt.strftime('%Y-%m-%d %H:%M')
    
    def _setup_handlers(self):
        """Set up MCP protocol handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="search_meetings",
                    description="Search meetings by title, content, or participants",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for meetings"
                            },
                            "limit": {
                                "type": "integer", 
                                "description": "Maximum number of results",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_meeting_details",
                    description="Get detailed information about a specific meeting",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "Meeting ID to retrieve details for"
                            }
                        },
                        "required": ["meeting_id"]
                    }
                ),
                Tool(
                    name="get_meeting_transcript",
                    description="Get transcript for a specific meeting",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string", 
                                "description": "Meeting ID to get transcript for"
                            }
                        },
                        "required": ["meeting_id"]
                    }
                ),
                Tool(
                    name="get_meeting_documents",
                    description="Get documents associated with a meeting",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "Meeting ID to get documents for" 
                            }
                        },
                        "required": ["meeting_id"]
                    }
                ),
                Tool(
                    name="analyze_meeting_patterns",
                    description="Analyze patterns across multiple meetings",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern_type": {
                                "type": "string",
                                "description": "Type of pattern to analyze (topics, participants, frequency)",
                                "enum": ["topics", "participants", "frequency"]
                            },
                            "date_range": {
                                "type": "object",
                                "properties": {
                                    "start_date": {"type": "string", "format": "date"},
                                    "end_date": {"type": "string", "format": "date"}
                                },
                                "description": "Optional date range for analysis"
                            }
                        },
                        "required": ["pattern_type"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            await self._ensure_cache_loaded()
            
            if name == "search_meetings":
                return await self._search_meetings(
                    query=arguments["query"],
                    limit=arguments.get("limit", 10)
                )
            elif name == "get_meeting_details":
                return await self._get_meeting_details(arguments["meeting_id"])
            elif name == "get_meeting_transcript":
                return await self._get_meeting_transcript(arguments["meeting_id"])
            elif name == "get_meeting_documents":
                return await self._get_meeting_documents(arguments["meeting_id"])
            elif name == "analyze_meeting_patterns":
                return await self._analyze_meeting_patterns(
                    pattern_type=arguments["pattern_type"],
                    date_range=arguments.get("date_range")
                )
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def _ensure_cache_loaded(self):
        """Ensure cache data is loaded."""
        if self.cache_data is None:
            await self._load_cache()
    
    async def _load_cache(self):
        """Load and parse Granola cache data."""
        try:
            cache_path = Path(self.cache_path)
            if not cache_path.exists():
                self.cache_data = CacheData()
                return
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Handle Granola's nested cache structure
            if 'cache' in raw_data and isinstance(raw_data['cache'], str):
                # Cache data is stored as a JSON string inside the 'cache' key
                actual_data = json.loads(raw_data['cache'])
                if 'state' in actual_data:
                    raw_data = actual_data['state']
                else:
                    raw_data = actual_data
            
            self.cache_data = await self._parse_cache_data(raw_data)
            
        except Exception as e:
            self.cache_data = CacheData()
            sys.stderr.write(f"Error loading cache: {e}\n")
    
    async def _parse_cache_data(self, raw_data: Dict[str, Any]) -> CacheData:
        """Parse raw cache data into structured models."""
        cache_data = CacheData()
        
        # Parse Granola documents (which are meetings)
        if "documents" in raw_data:
            for meeting_id, meeting_data in raw_data["documents"].items():
                try:
                    # Extract participants from people array
                    participants = []
                    if "people" in meeting_data and isinstance(meeting_data["people"], list):
                        participants = [person.get("name", "") for person in meeting_data["people"] if person.get("name")]
                    
                    # Parse creation date
                    created_at = meeting_data.get("created_at")
                    if created_at:
                        # Handle Granola's ISO format
                        if created_at.endswith('Z'):
                            created_at = created_at[:-1] + '+00:00'
                        meeting_date = datetime.fromisoformat(created_at)
                    else:
                        meeting_date = datetime.now()
                    
                    metadata = MeetingMetadata(
                        id=meeting_id,
                        title=meeting_data.get("title", "Untitled Meeting"),
                        date=meeting_date,
                        duration=None,  # Granola doesn't store duration in this format
                        participants=participants,
                        meeting_type=meeting_data.get("type", "meeting"),
                        platform=None  # Not stored in Granola cache
                    )
                    cache_data.meetings[meeting_id] = metadata
                except Exception as e:
                    sys.stderr.write(f"Error parsing meeting {meeting_id}: {e}\n")
        
        # Parse Granola transcripts (list format)
        if "transcripts" in raw_data:
            for transcript_id, transcript_data in raw_data["transcripts"].items():
                try:
                    # Use transcript_id as meeting_id (they match in Granola)
                    meeting_id = transcript_id
                    
                    # Extract transcript content and speakers
                    content_parts = []
                    speakers_set = set()
                    
                    if isinstance(transcript_data, list):
                        # Granola format: list of speech segments
                        for segment in transcript_data:
                            if isinstance(segment, dict) and "text" in segment:
                                text = segment["text"].strip()
                                if text:
                                    content_parts.append(text)
                                
                                # Extract speaker info if available
                                if "source" in segment:
                                    speakers_set.add(segment["source"])
                    
                    elif isinstance(transcript_data, dict):
                        # Fallback: dict format (legacy or different structure)
                        if "content" in transcript_data:
                            content_parts.append(transcript_data["content"])
                        elif "text" in transcript_data:
                            content_parts.append(transcript_data["text"])
                        elif "transcript" in transcript_data:
                            content_parts.append(transcript_data["transcript"])
                        
                        # Extract speakers if available
                        if "speakers" in transcript_data:
                            speakers_set.update(transcript_data["speakers"])
                    
                    # Combine all content and create transcript
                    if content_parts:
                        full_content = " ".join(content_parts)
                        speakers_list = list(speakers_set) if speakers_set else []
                        
                        transcript = MeetingTranscript(
                            meeting_id=meeting_id,
                            content=full_content,
                            speakers=speakers_list,
                            language=None,  # Not typically stored in segment format
                            confidence=None  # Would need to be calculated from segments
                        )
                        cache_data.transcripts[meeting_id] = transcript
                        
                except Exception as e:
                    sys.stderr.write(f"Error parsing transcript {transcript_id}: {e}\n")
        
        # Extract document content from Granola documents
        if "documents" in raw_data:
            for doc_id, doc_data in raw_data["documents"].items():
                try:
                    # Extract content from various Granola fields
                    # Check ALL fields (not elif) to combine content from multiple sources
                    content_parts = []
                    
                    # Try notes_plain (cleanest format)
                    notes_plain = doc_data.get("notes_plain")
                    if notes_plain and isinstance(notes_plain, str) and notes_plain.strip():
                        content_parts.append(notes_plain.strip())
                    
                    # Try notes_markdown
                    notes_markdown = doc_data.get("notes_markdown")
                    if notes_markdown and isinstance(notes_markdown, str) and notes_markdown.strip():
                        # Only add if we don't already have notes_plain (to avoid duplicates)
                        if not notes_plain or not notes_plain.strip():
                            content_parts.append(notes_markdown.strip())
                    
                    # Try to extract from structured notes field
                    notes_dict = doc_data.get("notes")
                    if notes_dict:
                        if isinstance(notes_dict, dict):
                            notes_content = self._extract_structured_notes(notes_dict)
                            if notes_content and notes_content.strip():
                                # Only add if we don't already have other notes
                                if not content_parts:
                                    content_parts.append(notes_content.strip())
                        elif isinstance(notes_dict, str) and notes_dict.strip():
                            # Sometimes notes might be a plain string
                            if not content_parts:
                                content_parts.append(notes_dict.strip())
                    
                    # Try other possible note field names
                    for field_name in ["note", "content", "body", "text"]:
                        field_value = doc_data.get(field_name)
                        if field_value and isinstance(field_value, str) and field_value.strip():
                            if not content_parts:
                                content_parts.append(field_value.strip())
                                break
                    
                    # Add overview if available
                    overview = doc_data.get("overview")
                    if overview and isinstance(overview, str) and overview.strip():
                        content_parts.append(f"Overview: {overview.strip()}")
                    
                    # Add summary if available  
                    summary = doc_data.get("summary")
                    if summary and isinstance(summary, str) and summary.strip():
                        content_parts.append(f"Summary: {summary.strip()}")
                    
                    content = "\n\n".join(content_parts) if content_parts else ""
                    
                    # Always create document if we have a meeting for it (even if content is empty)
                    # This ensures the document exists and can be checked/debugged
                    if doc_id in cache_data.meetings:
                        meeting = cache_data.meetings[doc_id]
                        document = MeetingDocument(
                            id=doc_id,
                            meeting_id=doc_id,
                            title=meeting.title,
                            content=content,
                            document_type="meeting_notes",
                            created_at=meeting.date,
                            tags=[]
                        )
                        cache_data.documents[doc_id] = document
                        
                        # Debug: log if we couldn't find content
                        if not content:
                            sys.stderr.write(f"Warning: No content found for meeting {doc_id} ({meeting.title}). Available fields: {list(doc_data.keys())}\n")
                        
                except Exception as e:
                    sys.stderr.write(f"Error extracting document content for {doc_id}: {e}\n")
                    import traceback
                    traceback.print_exc(file=sys.stderr)
        
        cache_data.last_updated = datetime.now()
        return cache_data
    
    def _extract_structured_notes(self, notes_data: Dict[str, Any]) -> str:
        """Extract text content from Granola's structured notes format."""
        try:
            if not isinstance(notes_data, dict) or 'content' not in notes_data:
                return ""
            
            def extract_text_from_content(content_list):
                text_parts = []
                if isinstance(content_list, list):
                    for item in content_list:
                        if isinstance(item, dict):
                            # Handle different content types
                            if item.get('type') == 'paragraph' and 'content' in item:
                                text_parts.append(extract_text_from_content(item['content']))
                            elif item.get('type') == 'text' and 'text' in item:
                                text_parts.append(item['text'])
                            elif 'content' in item:
                                text_parts.append(extract_text_from_content(item['content']))
                return ' '.join(text_parts)
            
            return extract_text_from_content(notes_data['content'])
            
        except Exception as e:
            sys.stderr.write(f"Error extracting structured notes: {e}\n")
            return ""
    
    def _parse_date_query(self, query: str) -> Optional[Tuple[datetime, datetime]]:
        """Parse date-related queries and return date range (start, end)."""
        query_lower = query.lower().strip()
        now = datetime.now(self.local_timezone)
        
        # Handle "this week" - Monday to Sunday of current week
        if "this week" in query_lower:
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            return (start, end)
        
        # Handle "last week" - Monday to Sunday of previous week
        if "last week" in query_lower:
            days_since_monday = now.weekday()
            last_monday = (now - timedelta(days=days_since_monday + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (last_monday + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            return (last_monday, end)
        
        # Handle "today"
        if query_lower == "today" or "today" in query_lower:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            return (start, end)
        
        # Handle "yesterday"
        if "yesterday" in query_lower:
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return (start, end)
        
        # Handle month queries like "November 2025", "Nov 2025", "November"
        month_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*(\d{4})?'
        month_match = re.search(month_pattern, query_lower)
        if month_match:
            month_name = month_match.group(1)
            year_str = month_match.group(2)
            
            month_map = {
                'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
                'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
                'july': 7, 'jul': 7, 'august': 8, 'aug': 8,
                'september': 9, 'sep': 9, 'october': 10, 'oct': 10,
                'november': 11, 'nov': 11, 'december': 12, 'dec': 12
            }
            
            month_num = month_map.get(month_name)
            if month_num:
                year = int(year_str) if year_str else now.year
                # Use UTC for month boundaries to avoid DST issues, then convert to local
                start_utc = datetime(year, month_num, 1, tzinfo=zoneinfo.ZoneInfo('UTC'))
                start = start_utc.astimezone(self.local_timezone).replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Get last day of month
                if month_num == 12:
                    end_utc = datetime(year + 1, 1, 1, tzinfo=zoneinfo.ZoneInfo('UTC')) - timedelta(microseconds=1)
                else:
                    end_utc = datetime(year, month_num + 1, 1, tzinfo=zoneinfo.ZoneInfo('UTC')) - timedelta(microseconds=1)
                end = end_utc.astimezone(self.local_timezone).replace(hour=23, minute=59, second=59, microsecond=999999)
                return (start, end)
        
        # Handle year queries like "2025"
        year_pattern = r'\b(20\d{2})\b'
        year_match = re.search(year_pattern, query_lower)
        if year_match:
            year = int(year_match.group(1))
            # Use UTC for year boundaries to avoid DST issues, then convert to local
            start_utc = datetime(year, 1, 1, tzinfo=zoneinfo.ZoneInfo('UTC'))
            start = start_utc.astimezone(self.local_timezone).replace(hour=0, minute=0, second=0, microsecond=0)
            end_utc = datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=zoneinfo.ZoneInfo('UTC'))
            end = end_utc.astimezone(self.local_timezone).replace(hour=23, minute=59, second=59, microsecond=999999)
            return (start, end)
        
        return None
    
    async def _search_meetings(self, query: str, limit: int = 10) -> List[TextContent]:
        """Search meetings by query."""
        if not self.cache_data:
            return [TextContent(type="text", text="No meeting data available")]
        
        query_lower = query.lower()
        results = []
        
        # Try to parse date query first
        date_range = self._parse_date_query(query)
        
        for meeting_id, meeting in self.cache_data.meetings.items():
            score = 0
            
            # If date range is specified, check if meeting falls within range
            if date_range:
                meeting_local_date = self._convert_to_local_time(meeting.date)
                if date_range[0] <= meeting_local_date <= date_range[1]:
                    score += 10  # High score for date matches
                else:
                    continue  # Skip meetings outside date range
            else:
                # Text-based search
                # Search in title
                if query_lower in meeting.title.lower():
                    score += 2
                
                # Search in participants
                for participant in meeting.participants:
                    if query_lower in participant.lower():
                        score += 1
                
                # Search in transcript content if available
                if meeting_id in self.cache_data.transcripts:
                    transcript = self.cache_data.transcripts[meeting_id]
                    if query_lower in transcript.content.lower():
                        score += 1
            
            if score > 0:
                results.append((score, meeting))
        
        # Sort by date (most recent first) if date query, otherwise by relevance
        if date_range:
            results.sort(key=lambda x: x[1].date, reverse=True)
        else:
            results.sort(key=lambda x: x[0], reverse=True)
        
        results = results[:limit]
        
        # Handle "this week" queries specially to show both past and upcoming
        if date_range and "this week" in query_lower:
            now = datetime.now(self.local_timezone)
            week_start = date_range[0].strftime("%B %d")
            week_end = date_range[1].strftime("%B %d")
            past_this_week = []
            upcoming_this_week = []
            
            # Fetch calendar events for this week
            calendar_events = []
            if self.google_calendar_enabled:
                try:
                    calendar_events = await self._fetch_calendar_events(date_range[0], date_range[1])
                except Exception as e:
                    sys.stderr.write(f"Error fetching calendar events: {e}\n")
            
            # Separate past and upcoming meetings within this week
            for score, meeting in results:
                meeting_local_date = self._convert_to_local_time(meeting.date)
                if meeting_local_date < now:
                    past_this_week.append((score, meeting))
                else:
                    upcoming_this_week.append((score, meeting))
            
            # Add calendar events to upcoming/past lists
            for event in calendar_events:
                event_local_date = self._convert_to_local_time(event['date'])
                if date_range[0] <= event_local_date <= date_range[1]:
                    # Create a MeetingMetadata-like object for calendar events
                    from types import SimpleNamespace
                    calendar_meeting = SimpleNamespace(
                        title=event['title'],
                        id=f"calendar_{event['id']}",
                        date=event['date'],
                        participants=event['participants'],
                        source='google_calendar'
                    )
                    if event_local_date < now:
                        past_this_week.append((10, calendar_meeting))
                    else:
                        upcoming_this_week.append((10, calendar_meeting))
            
            output_lines = []
            
            if upcoming_this_week or past_this_week:
                
                if upcoming_this_week:
                    output_lines.append(f"## Upcoming This Week ({week_start} - {week_end})\n")
                    # Sort by date, handling both timezone-aware and naive datetimes
                    def get_sort_date(item):
                        date = item[1].date
                        if date.tzinfo is None:
                            # Make naive datetime timezone-aware for comparison
                            return date.replace(tzinfo=self.local_timezone)
                        return date
                    upcoming_this_week.sort(key=lambda x: get_sort_date(x))  # Sort ascending (earliest first)
                    for score, meeting in upcoming_this_week:
                        meeting_local_date = self._convert_to_local_time(meeting.date)
                        source_label = "📅 Calendar" if hasattr(meeting, 'source') and meeting.source == 'google_calendar' else "🎙️ Granola"
                        output_lines.append(f"• **{meeting.title}** {source_label}")
                        if not hasattr(meeting, 'source') or meeting.source != 'google_calendar':
                            output_lines.append(f"  ID: {meeting.id}")
                        output_lines.append(f"  Date: {self._format_local_time(meeting.date)}")
                        if meeting.participants:
                            output_lines.append(f"  Participants: {', '.join(meeting.participants)}")
                        output_lines.append("")
                
                if past_this_week:
                    if upcoming_this_week:
                        output_lines.append("\n## Past This Week\n")
                    else:
                        output_lines.append(f"## Meetings This Week ({week_start} - {week_end})\n")
                    # Sort by date, handling both timezone-aware and naive datetimes
                    def get_sort_date(item):
                        date = item[1].date
                        if date.tzinfo is None:
                            # Make naive datetime timezone-aware for comparison
                            return date.replace(tzinfo=self.local_timezone)
                        return date
                    past_this_week.sort(key=lambda x: get_sort_date(x), reverse=True)  # Sort descending (most recent first)
                    for score, meeting in past_this_week:
                        source_label = "📅 Calendar" if hasattr(meeting, 'source') and meeting.source == 'google_calendar' else "🎙️ Granola"
                        output_lines.append(f"• **{meeting.title}** {source_label}")
                        if not hasattr(meeting, 'source') or meeting.source != 'google_calendar':
                            output_lines.append(f"  ID: {meeting.id}")
                        output_lines.append(f"  Date: {self._format_local_time(meeting.date)}")
                        if meeting.participants:
                            output_lines.append(f"  Participants: {', '.join(meeting.participants)}")
                        output_lines.append("")
                
                return [TextContent(type="text", text="\n".join(output_lines))]
            
            # If no meetings this week, show upcoming scheduled meetings and recent past
            else:
                # Look for upcoming meetings (future dates) - though Granola cache typically only has past meetings
                upcoming_future = []
                for meeting_id, meeting in self.cache_data.meetings.items():
                    meeting_local_date = self._convert_to_local_time(meeting.date)
                    if meeting_local_date > now:
                        upcoming_future.append((0, meeting))
                
                # Also get recent past meetings
                two_weeks_ago = now - timedelta(days=14)
                recent_past = []
                for meeting_id, meeting in self.cache_data.meetings.items():
                    meeting_local_date = self._convert_to_local_time(meeting.date)
                    if two_weeks_ago <= meeting_local_date < now:
                        recent_past.append((0, meeting))
                
                # Try to fetch calendar events if no Granola meetings found
                calendar_events = []
                if self.google_calendar_enabled:
                    try:
                        calendar_events = await self._fetch_calendar_events(date_range[0], date_range[1])
                        # Filter to upcoming events
                        upcoming_calendar = [e for e in calendar_events if self._convert_to_local_time(e['date']) > now]
                        if upcoming_calendar:
                            output_lines = [f"## Upcoming This Week ({week_start} - {week_end})\n\n"]
                            # Sort by date, ensuring timezone-aware
                            def get_event_date(event):
                                date = event['date']
                                if date.tzinfo is None:
                                    return date.replace(tzinfo=self.local_timezone)
                                return date
                            upcoming_calendar.sort(key=get_event_date)
                            for event in upcoming_calendar[:limit]:
                                event_local_date = self._convert_to_local_time(event['date'])
                                output_lines.append(f"• **{event['title']}** 📅 Calendar")
                                output_lines.append(f"  Date: {self._format_local_time(event['date'])}")
                                if event.get('location'):
                                    output_lines.append(f"  Location: {event['location']}")
                                if event['participants']:
                                    output_lines.append(f"  Participants: {', '.join(event['participants'])}")
                                output_lines.append("")
                            return [TextContent(type="text", text="\n".join(output_lines))]
                    except Exception as e:
                        sys.stderr.write(f"Error fetching calendar events: {e}\n")
                
                output_lines = [f"No recorded meetings found for this week ({week_start} - {week_end}).\n\n"]
                if not self.google_calendar_enabled:
                    output_lines.append("**Note:** Granola's cache only contains meetings that have already been recorded. ")
                    output_lines.append("To see your upcoming scheduled meetings, please configure Google Calendar integration.\n\n")
                
                if upcoming_future:
                    upcoming_future.sort(key=lambda x: x[1].date)  # Sort ascending
                    upcoming_future = upcoming_future[:5]  # Limit to 5 upcoming
                    output_lines.append("## Upcoming Scheduled Meetings (from Granola cache)\n")
                    for score, meeting in upcoming_future:
                        output_lines.append(f"• **{meeting.title}** ({meeting.id})")
                        output_lines.append(f"  Date: {self._format_local_time(meeting.date)}")
                        if meeting.participants:
                            output_lines.append(f"  Participants: {', '.join(meeting.participants)}")
                        output_lines.append("")
                    output_lines.append("")
                
                if recent_past:
                    recent_past.sort(key=lambda x: x[1].date, reverse=True)
                    recent_past = recent_past[:5]  # Limit to 5 recent
                    output_lines.append("## Recent Past Meetings\n")
                    for score, meeting in recent_past:
                        output_lines.append(f"• **{meeting.title}** ({meeting.id})")
                        output_lines.append(f"  Date: {self._format_local_time(meeting.date)}")
                        if meeting.participants:
                            output_lines.append(f"  Participants: {', '.join(meeting.participants)}")
                        output_lines.append("")
                
                return [TextContent(type="text", text="\n".join(output_lines))]
        
        if not results:
            return [TextContent(type="text", text=f"No meetings found matching '{query}'")]
        
        output_lines = [f"Found {len(results)} meeting(s) matching '{query}':\n"]
        
        for score, meeting in results:
            output_lines.append(f"• **{meeting.title}** ({meeting.id})")
            output_lines.append(f"  Date: {self._format_local_time(meeting.date)}")
            if meeting.participants:
                output_lines.append(f"  Participants: {', '.join(meeting.participants)}")
            output_lines.append("")
        
        return [TextContent(type="text", text="\n".join(output_lines))]
    
    async def _get_meeting_details(self, meeting_id: str) -> List[TextContent]:
        """Get detailed meeting information."""
        if not self.cache_data or meeting_id not in self.cache_data.meetings:
            return [TextContent(type="text", text=f"Meeting '{meeting_id}' not found")]
        
        meeting = self.cache_data.meetings[meeting_id]
        
        details = [
            f"# Meeting Details: {meeting.title}\n",
            f"**ID:** {meeting.id}",
            f"**Date:** {self._format_local_time(meeting.date)}",
        ]
        
        if meeting.duration:
            details.append(f"**Duration:** {meeting.duration} minutes")
        
        if meeting.participants:
            details.append(f"**Participants:** {', '.join(meeting.participants)}")
        
        if meeting.meeting_type:
            details.append(f"**Type:** {meeting.meeting_type}")
        
        if meeting.platform:
            details.append(f"**Platform:** {meeting.platform}")
        
        # Add document count
        doc_count = sum(1 for doc in self.cache_data.documents.values() 
                       if doc.meeting_id == meeting_id)
        if doc_count > 0:
            details.append(f"**Documents:** {doc_count}")
        
        # Add transcript availability
        if meeting_id in self.cache_data.transcripts:
            details.append("**Transcript:** Available")
        
        return [TextContent(type="text", text="\n".join(details))]
    
    async def _get_meeting_transcript(self, meeting_id: str) -> List[TextContent]:
        """Get meeting transcript."""
        if not self.cache_data:
            return [TextContent(type="text", text="No meeting data available")]
        
        if meeting_id not in self.cache_data.transcripts:
            return [TextContent(type="text", text=f"No transcript available for meeting '{meeting_id}'")]
        
        transcript = self.cache_data.transcripts[meeting_id]
        meeting = self.cache_data.meetings.get(meeting_id)
        
        output = [f"# Transcript: {meeting.title if meeting else meeting_id}\n"]
        
        if transcript.speakers:
            output.append(f"**Speakers:** {', '.join(transcript.speakers)}")
        
        if transcript.language:
            output.append(f"**Language:** {transcript.language}")
        
        if transcript.confidence:
            output.append(f"**Confidence:** {transcript.confidence:.2%}")
        
        output.append("\n## Transcript Content\n")
        output.append(transcript.content)
        
        return [TextContent(type="text", text="\n".join(output))]
    
    async def _get_meeting_documents(self, meeting_id: str) -> List[TextContent]:
        """Get meeting documents."""
        if not self.cache_data:
            return [TextContent(type="text", text="No meeting data available")]
        
        documents = [doc for doc in self.cache_data.documents.values() 
                    if doc.meeting_id == meeting_id]
        
        if not documents:
            return [TextContent(type="text", text=f"No documents found for meeting '{meeting_id}'")]
        
        meeting = self.cache_data.meetings.get(meeting_id)
        output = [f"# Documents: {meeting.title if meeting else meeting_id}\n"]
        output.append(f"Found {len(documents)} document(s):\n")
        
        for doc in documents:
            output.append(f"## {doc.title}")
            output.append(f"**Type:** {doc.document_type}")
            output.append(f"**Created:** {self._format_local_time(doc.created_at)}")
            
            if doc.tags:
                output.append(f"**Tags:** {', '.join(doc.tags)}")
            
            output.append(f"\n{doc.content}\n")
            output.append("---\n")
        
        return [TextContent(type="text", text="\n".join(output))]
    
    async def _analyze_meeting_patterns(self, pattern_type: str, date_range: Optional[Dict] = None) -> List[TextContent]:
        """Analyze patterns across meetings."""
        if not self.cache_data:
            return [TextContent(type="text", text="No meeting data available")]
        
        meetings = list(self.cache_data.meetings.values())
        
        # Filter by date range if provided
        if date_range:
            start_date = datetime.fromisoformat(date_range.get("start_date", "1900-01-01"))
            end_date = datetime.fromisoformat(date_range.get("end_date", "2100-01-01"))
            meetings = [m for m in meetings if start_date <= m.date <= end_date]
        
        if pattern_type == "participants":
            return await self._analyze_participant_patterns(meetings)
        elif pattern_type == "frequency":
            return await self._analyze_frequency_patterns(meetings)
        elif pattern_type == "topics":
            return await self._analyze_topic_patterns(meetings)
        else:
            return [TextContent(type="text", text=f"Unknown pattern type: {pattern_type}")]
    
    async def _analyze_participant_patterns(self, meetings: List[MeetingMetadata]) -> List[TextContent]:
        """Analyze participant patterns."""
        participant_counts = {}
        
        for meeting in meetings:
            for participant in meeting.participants:
                participant_counts[participant] = participant_counts.get(participant, 0) + 1
        
        if not participant_counts:
            return [TextContent(type="text", text="No participant data found")]
        
        sorted_participants = sorted(participant_counts.items(), key=lambda x: x[1], reverse=True)
        
        output = [
            f"# Participant Analysis ({len(meetings)} meetings)\n",
            "## Most Active Participants\n"
        ]
        
        for participant, count in sorted_participants[:10]:
            output.append(f"• **{participant}:** {count} meetings")
        
        return [TextContent(type="text", text="\n".join(output))]
    
    async def _analyze_frequency_patterns(self, meetings: List[MeetingMetadata]) -> List[TextContent]:
        """Analyze meeting frequency patterns."""
        if not meetings:
            return [TextContent(type="text", text="No meetings found for analysis")]
        
        # Group by month
        monthly_counts = {}
        for meeting in meetings:
            month_key = meeting.date.strftime("%Y-%m")
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        output = [
            f"# Meeting Frequency Analysis ({len(meetings)} meetings)\n",
            "## Meetings by Month\n"
        ]
        
        for month, count in sorted(monthly_counts.items()):
            output.append(f"• **{month}:** {count} meetings")
        
        avg_per_month = len(meetings) / len(monthly_counts) if monthly_counts else 0
        output.append(f"\n**Average per month:** {avg_per_month:.1f}")
        
        return [TextContent(type="text", text="\n".join(output))]
    
    async def _analyze_topic_patterns(self, meetings: List[MeetingMetadata]) -> List[TextContent]:
        """Analyze topic patterns from meeting titles."""
        if not meetings:
            return [TextContent(type="text", text="No meetings found for analysis")]
        
        # Simple keyword extraction from titles
        word_counts = {}
        for meeting in meetings:
            words = meeting.title.lower().split()
            for word in words:
                # Filter out common words
                if len(word) > 3 and word not in ['meeting', 'call', 'sync', 'with']:
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        if not word_counts:
            return [TextContent(type="text", text="No significant topics found in meeting titles")]
        
        sorted_topics = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        output = [
            f"# Topic Analysis ({len(meetings)} meetings)\n",
            "## Most Common Topics (from titles)\n"
        ]
        
        for topic, count in sorted_topics[:15]:
            output.append(f"• **{topic}:** {count} mentions")
        
        return [TextContent(type="text", text="\n".join(output))]
    
    def run(self, transport_type: str = "stdio"):
        """Run the server."""
        import asyncio
        from mcp.server.stdio import stdio_server
        from mcp.types import ServerCapabilities
        
        if transport_type == "stdio":
            async def main():
                # Set up server capabilities for tool support
                capabilities = ServerCapabilities(
                    tools={}  # Empty dict indicates tool support is available
                )
                
                options = InitializationOptions(
                    server_name="granola-mcp-server",
                    server_version="0.1.0",
                    capabilities=capabilities
                )
                
                async with stdio_server() as (read_stream, write_stream):
                    await self.server.run(read_stream, write_stream, options)
            
            return asyncio.run(main())
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}. Only 'stdio' is supported.")


def main():
    """Main entry point for the server."""
    # Get Google credentials from environment variables
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    google_refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    
    server = GranolaMCPServer(
        google_client_id=google_client_id,
        google_client_secret=google_client_secret,
        google_refresh_token=google_refresh_token
    )
    server.run()