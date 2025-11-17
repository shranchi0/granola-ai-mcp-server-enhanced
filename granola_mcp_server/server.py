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

# Sentence transformers for semantic search (optional)
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None
    np = None

# HTTP client for Turbopuffer (optional)
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

# OpenAI for intelligent analysis (optional)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


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
        
        # Initialize embedding model for semantic search
        # Using Turbopuffer for shared team vector database
        self.embedding_model = None
        self.turbopuffer_api_key = os.getenv("TURBOPUFFER_API_KEY")
        self.turbopuffer_namespace = os.getenv("TURBOPUFFER_NAMESPACE", "granola-meetings")
        self.turbopuffer_base_url = "https://api.turbopuffer.com/v1"
        
        # Always initialize local model for generating embeddings (needed for Turbopuffer)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Use a lightweight, fast model optimized for semantic similarity
                # all-MiniLM-L6-v2 is small (~80MB) and fast while being effective
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                sys.stderr.write(f"Warning: Could not load embedding model: {e}\n")
                self.embedding_model = None
        
        # Validate Turbopuffer configuration
        self.turbopuffer_enabled = (
            HTTPX_AVAILABLE and 
            self.turbopuffer_api_key and 
            self.embedding_model is not None
        )
        
        if not self.turbopuffer_enabled:
            if not HTTPX_AVAILABLE:
                sys.stderr.write("Warning: httpx not available, install with: pip install httpx\n")
            elif not self.turbopuffer_api_key:
                sys.stderr.write("Warning: TURBOPUFFER_API_KEY not set\n")
            elif not self.embedding_model:
                sys.stderr.write("Warning: Embedding model not available\n")
        
        # Initialize OpenAI client for intelligent analysis
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        if OPENAI_AVAILABLE and self.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                sys.stderr.write(f"Warning: Could not initialize OpenAI client: {e}\n")
                self.openai_client = None
        elif OPENAI_AVAILABLE and not self.openai_api_key:
            sys.stderr.write("Warning: OPENAI_API_KEY not set - intelligent search will be unavailable\n")
            
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
                ),
                Tool(
                    name="find_similar_companies",
                    description="Find meetings with similar companies using semantic search. Use this to find companies in similar industries, with similar business models, or solving similar problems. Examples: 'AI for HR companies', 'recruiting platforms', 'similar to HeyMilo'",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Description of the type of company or industry to search for (e.g., 'AI recruiting companies', 'HR tech platforms', 'similar to [company name]')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of similar meetings to return",
                                "default": 10
                            },
                            "min_similarity": {
                                "type": "number",
                                "description": "Minimum similarity score (0-1) to include results",
                                "default": 0.3
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="search_companies_by_category",
                    description="Intelligently search for companies by category using AI analysis. This uses GPT to understand what type of companies you're looking for and analyzes meeting content to find matches. Examples: 'devtools companies', 'AI companies', 'HR tech companies', 'fintech startups'. Much more intelligent than keyword search.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Category or type of companies to find (e.g., 'devtools', 'AI companies', 'HR tech', 'fintech', 'SaaS companies')"
                            },
                            "date_range": {
                                "type": "object",
                                "properties": {
                                    "start_date": {"type": "string", "format": "date"},
                                    "end_date": {"type": "string", "format": "date"}
                                },
                                "description": "Optional date range to filter meetings (e.g., last 2 weeks, last month)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of companies to return",
                                "default": 20
                            }
                        },
                        "required": ["category"]
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
            elif name == "find_similar_companies":
                return await self._find_similar_companies(
                    query=arguments["query"],
                    limit=arguments.get("limit", 10),
                    min_similarity=arguments.get("min_similarity", 0.3)
                )
            elif name == "search_companies_by_category":
                return await self._search_companies_by_category(
                    category=arguments["category"],
                    date_range=arguments.get("date_range"),
                    limit=arguments.get("limit", 20)
                )
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def _ensure_cache_loaded(self):
        """Ensure cache data is loaded."""
        if self.cache_data is None:
            await self._load_cache()
            # Sync meetings to Turbopuffer after loading cache
            if self.turbopuffer_enabled:
                await self._sync_meetings_to_turbopuffer()
    
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
                    
                    # Try notes_plain (cleanest format) - prioritize this
                    notes_plain = doc_data.get("notes_plain")
                    if notes_plain is not None and isinstance(notes_plain, str) and notes_plain.strip():
                        content_parts.append(notes_plain.strip())
                    
                    # Try notes_markdown
                    notes_markdown = doc_data.get("notes_markdown")
                    if notes_markdown is not None and isinstance(notes_markdown, str) and notes_markdown.strip():
                        # Only add if we don't already have notes_plain (to avoid duplicates)
                        notes_plain_val = doc_data.get("notes_plain") or ""
                        if not isinstance(notes_plain_val, str) or not notes_plain_val.strip():
                            content_parts.append(notes_markdown.strip())
                    
                    # Try to extract from structured notes field (check multiple possible structures)
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
                        elif isinstance(notes_dict, list):
                            # Notes might be a list of content blocks
                            for item in notes_dict:
                                if isinstance(item, str) and item.strip():
                                    if not content_parts:
                                        content_parts.append(item.strip())
                                        break
                                elif isinstance(item, dict):
                                    extracted = self._extract_structured_notes(item)
                                    if extracted and extracted.strip():
                                        if not content_parts:
                                            content_parts.append(extracted.strip())
                                            break
                    
                    # Try other possible note field names (more comprehensive list)
                    for field_name in ["note", "content", "body", "text", "description", "details", "summary_text"]:
                        field_value = doc_data.get(field_name)
                        if field_value:
                            if isinstance(field_value, str) and field_value.strip():
                                if not content_parts:
                                    content_parts.append(field_value.strip())
                                    break
                            elif isinstance(field_value, dict):
                                # Try to extract from nested dict
                                extracted = self._extract_structured_notes(field_value)
                                if extracted and extracted.strip():
                                    if not content_parts:
                                        content_parts.append(extracted.strip())
                                        break
                    
                    # Check for nested content structures
                    if not content_parts:
                        # Try checking if content is nested in a 'content' or 'data' key
                        for nested_key in ["content", "data", "value"]:
                            nested_data = doc_data.get(nested_key)
                            if nested_data:
                                if isinstance(nested_data, str) and nested_data.strip():
                                    content_parts.append(nested_data.strip())
                                    break
                                elif isinstance(nested_data, dict):
                                    extracted = self._extract_structured_notes(nested_data)
                                    if extracted and extracted.strip():
                                        content_parts.append(extracted.strip())
                                        break
                                elif isinstance(nested_data, list):
                                    # Try to extract text from list items
                                    text_items = []
                                    for item in nested_data:
                                        if isinstance(item, str):
                                            text_items.append(item)
                                        elif isinstance(item, dict):
                                            extracted = self._extract_structured_notes(item)
                                            if extracted:
                                                text_items.append(extracted)
                                    if text_items:
                                        content_parts.append("\n".join(text_items))
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
                            # Show available fields and their types
                            field_info = []
                            for key, value in doc_data.items():
                                value_type = type(value).__name__
                                if isinstance(value, str):
                                    preview = value[:100] + "..." if len(value) > 100 else value
                                    field_info.append(f"  {key}: {value_type} = '{preview}'")
                                elif isinstance(value, (dict, list)):
                                    field_info.append(f"  {key}: {value_type} (len={len(value)})")
                                else:
                                    field_info.append(f"  {key}: {value_type} = {str(value)[:100]}")
                            
                            sys.stderr.write(f"Warning: No content found for meeting {doc_id} ({meeting.title})\n")
                            sys.stderr.write(f"Available fields:\n" + "\n".join(field_info) + "\n")
                        
                except Exception as e:
                    sys.stderr.write(f"Error extracting document content for {doc_id}: {e}\n")
                    import traceback
                    traceback.print_exc(file=sys.stderr)
        
        cache_data.last_updated = datetime.now()
        return cache_data
    
    def _extract_structured_notes(self, notes_data: Dict[str, Any]) -> str:
        """Extract text content from Granola's structured notes format (ProseMirror/TipTap)."""
        try:
            if not isinstance(notes_data, dict):
                return ""
            
            def extract_text_from_content(content_list):
                """Recursively extract text from ProseMirror/TipTap structure."""
                text_parts = []
                if isinstance(content_list, list):
                    for item in content_list:
                        if isinstance(item, dict):
                            item_type = item.get('type', '')
                            
                            # Direct text node
                            if item_type == 'text' and 'text' in item:
                                text_parts.append(item['text'])
                            
                            # Paragraph, heading, or other block with nested content
                            elif 'content' in item:
                                nested_text = extract_text_from_content(item['content'])
                                if nested_text:
                                    text_parts.append(nested_text)
                            
                            # Some nodes have text directly
                            elif 'text' in item and isinstance(item['text'], str):
                                text_parts.append(item['text'])
                            
                            # Check attrs for text (sometimes text is in attributes)
                            elif 'attrs' in item and isinstance(item['attrs'], dict):
                                for attr_key in ['text', 'content', 'data']:
                                    if attr_key in item['attrs']:
                                        attr_value = item['attrs'][attr_key]
                                        if isinstance(attr_value, str) and attr_value.strip():
                                            text_parts.append(attr_value)
                            
                            # Recursively check all dict values
                            else:
                                for value in item.values():
                                    if isinstance(value, (dict, list)):
                                        nested_text = extract_text_from_content(value if isinstance(value, list) else [value])
                                        if nested_text:
                                            text_parts.append(nested_text)
                
                return ' '.join(text_parts)
            
            # Handle both direct content and nested structure
            if 'content' in notes_data:
                return extract_text_from_content(notes_data['content'])
            else:
                # Try to extract from the whole structure
                return extract_text_from_content([notes_data])
            
        except Exception as e:
            sys.stderr.write(f"Error extracting structured notes: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
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
    
    async def _upsert_to_turbopuffer(self, rows: List[Dict[str, Any]]) -> None:
        """Upsert rows to Turbopuffer."""
        if not self.turbopuffer_enabled:
            return
        
        try:
            url = f"{self.turbopuffer_base_url}/namespaces/{self.turbopuffer_namespace}"
            headers = {
                "Authorization": f"Bearer {self.turbopuffer_api_key}",
                "Content-Type": "application/json"
            }
            
            # Turbopuffer expects upsert_rows with schema
            payload = {
                "upsert_rows": rows,
                "distance_metric": "cosine_distance",
                "schema": {
                    "text": {
                        "type": "string",
                        "full_text_search": True
                    },
                    "meeting_id": {"type": "string"},
                    "title": {"type": "string"},
                    "date": {"type": "string"},
                    "participants": {"type": "string"}
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code in [200, 201]:
                    # Success - namespace will be created automatically on first upsert
                    sys.stderr.write(f"Successfully upserted {len(rows)} meetings to Turbopuffer namespace '{self.turbopuffer_namespace}'\n")
                else:
                    error_text = response.text
                    sys.stderr.write(f"Turbopuffer API error {response.status_code}: {error_text}\n")
                    response.raise_for_status()
                
        except httpx.HTTPStatusError as e:
            error_text = e.response.text if hasattr(e.response, 'text') else str(e)
            sys.stderr.write(f"Error upserting to Turbopuffer (HTTP {e.response.status_code}): {error_text}\n")
        except Exception as e:
            sys.stderr.write(f"Error upserting to Turbopuffer: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    async def _query_turbopuffer(self, query: str, limit: int = 10, min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """Query Turbopuffer for similar meetings."""
        if not self.turbopuffer_enabled:
            return []
        
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)[0].tolist()
            
            url = f"{self.turbopuffer_base_url}/namespaces/{self.turbopuffer_namespace}/query"
            headers = {
                "Authorization": f"Bearer {self.turbopuffer_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "vector": query_embedding,
                "text_query": query,  # Hybrid search: both vector and text
                "limit": limit,
                "filters": {}  # Can add filters here if needed
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for result in data.get("results", []):
                    # Turbopuffer returns similarity as distance, convert to similarity score
                    # cosine_distance ranges from 0-2, where 0 is most similar
                    # Convert to similarity: similarity = 1 - (distance / 2)
                    distance = result.get("distance", 2.0)
                    similarity = max(0, 1 - (distance / 2))
                    
                    if similarity >= min_similarity:
                        results.append({
                            "id": result.get("id"),
                            "similarity": similarity,
                            "metadata": result.get("metadata", {})
                        })
                
                return results
                
        except Exception as e:
            sys.stderr.write(f"Error querying Turbopuffer: {e}\n")
            return []
    
    async def _sync_meetings_to_turbopuffer(self) -> None:
        """Sync all meetings from cache to Turbopuffer."""
        if not self.turbopuffer_enabled:
            sys.stderr.write("Turbopuffer not enabled, skipping sync\n")
            return
        
        if not self.cache_data:
            sys.stderr.write("No cache data available, skipping Turbopuffer sync\n")
            return
        
        try:
            sys.stderr.write(f"Starting sync to Turbopuffer namespace '{self.turbopuffer_namespace}'...\n")
            rows = []
            
            for meeting_id, meeting in self.cache_data.meetings.items():
                # Build rich text representation for embedding
                text_parts = [meeting.title]
                
                if meeting.participants:
                    text_parts.append(f"Participants: {', '.join(meeting.participants)}")
                
                # Add document content if available
                if meeting_id in self.cache_data.documents:
                    doc = self.cache_data.documents[meeting_id]
                    if doc.content:
                        # Use more content for better embeddings (up to 2000 chars)
                        content_snippet = doc.content[:2000].replace('\n', ' ')
                        text_parts.append(f"Notes: {content_snippet}")
                
                # Add transcript snippet if available
                if meeting_id in self.cache_data.transcripts:
                    transcript = self.cache_data.transcripts[meeting_id]
                    if transcript.content:
                        transcript_snippet = transcript.content[:2000].replace('\n', ' ')
                        text_parts.append(f"Transcript: {transcript_snippet}")
                
                meeting_text = " | ".join(text_parts)
                
                # Generate embedding
                embedding = self.embedding_model.encode([meeting_text], convert_to_numpy=True)[0].tolist()
                
                # Prepare row for Turbopuffer
                row = {
                    "id": meeting_id,
                    "vector": embedding,
                    "text": meeting_text,
                    "meeting_id": meeting_id,
                    "title": meeting.title,
                    "date": meeting.date.isoformat(),
                    "participants": ", ".join(meeting.participants) if meeting.participants else ""
                }
                
                rows.append(row)
            
            if rows:
                # Upsert in batches of 100 (Turbopuffer limit)
                batch_size = 100
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    await self._upsert_to_turbopuffer(batch)
                
                sys.stderr.write(f"Synced {len(rows)} meetings to Turbopuffer\n")
                
        except Exception as e:
            sys.stderr.write(f"Error syncing meetings to Turbopuffer: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    async def _find_similar_companies(self, query: str, limit: int = 10, min_similarity: float = 0.3) -> List[TextContent]:
        """Find meetings with similar companies using semantic search via Turbopuffer."""
        if not self.turbopuffer_enabled:
            return [TextContent(
                type="text", 
                text="Semantic search requires Turbopuffer. Please set TURBOPUFFER_API_KEY environment variable."
            )]
        
        try:
            # Query Turbopuffer for similar meetings (searches across all team members' meetings)
            turbopuffer_results = await self._query_turbopuffer(query, limit=limit * 2, min_similarity=min_similarity)
            
            if not turbopuffer_results:
                return [TextContent(
                    type="text", 
                    text=f"No similar companies found matching '{query}' (minimum similarity: {min_similarity:.2f})"
                )]
            
            # Get meeting details from cache for results
            results = []
            for result in turbopuffer_results[:limit]:
                meeting_id = result["id"]
                similarity_score = result["similarity"]
                metadata = result.get("metadata", {})
                
                # Try to get meeting from local cache first
                meeting = None
                if self.cache_data and meeting_id in self.cache_data.meetings:
                    meeting = self.cache_data.meetings[meeting_id]
                else:
                    # Meeting is from another team member, use metadata
                    from datetime import datetime
                    meeting = MeetingMetadata(
                        id=meeting_id,
                        title=metadata.get("title", "Unknown Meeting"),
                        date=datetime.fromisoformat(metadata.get("date", "2000-01-01T00:00:00")),
                        participants=metadata.get("participants", "").split(", ") if metadata.get("participants") else [],
                        meeting_type=None,
                        platform=None
                    )
                
                results.append((similarity_score, meeting_id, meeting, metadata))
            
            if not results:
                return [TextContent(
                    type="text", 
                    text=f"No similar companies found matching '{query}' (minimum similarity: {min_similarity:.2f})"
                )]
            
            # Format results
            output = [f"# Similar Companies Found (Team-Wide Search)\n\n"]
            output.append(f"Query: **{query}**\n")
            output.append(f"Found {len(results)} similar meeting(s) across all team members:\n\n")
            
            for similarity_score, meeting_id, meeting, metadata in results:
                output.append(f"## {meeting.title}")
                output.append(f"**Similarity:** {similarity_score:.2%}")
                output.append(f"**Date:** {self._format_local_time(meeting.date)}")
                output.append(f"**ID:** {meeting_id}")
                
                if meeting.participants:
                    output.append(f"**Participants:** {', '.join(meeting.participants)}")
                
                # Add note if meeting is from another team member
                if meeting_id not in (self.cache_data.meetings if self.cache_data else {}):
                    output.append(f"*Note: This meeting is from another team member*")
                
                output.append("")
            
            return [TextContent(type="text", text="\n".join(output))]
            
        except Exception as e:
            sys.stderr.write(f"Error in semantic search: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
            return [TextContent(
                type="text", 
                text=f"Error performing similarity search: {str(e)}"
            )]
    
    async def _search_companies_by_category(self, category: str, date_range: Optional[Dict] = None, limit: int = 20) -> List[TextContent]:
        """Intelligently search for companies by category using GPT analysis."""
        if not self.openai_client:
            return [TextContent(
                type="text",
                text="Intelligent search requires OpenAI API. Please set OPENAI_API_KEY environment variable."
            )]
        
        if not self.cache_data or not self.cache_data.meetings:
            return [TextContent(type="text", text="No meetings found in cache")]
        
        try:
            # Filter meetings by date range if provided
            meetings_to_analyze = []
            for meeting_id, meeting in self.cache_data.meetings.items():
                if date_range:
                    start_date = datetime.fromisoformat(date_range.get("start_date", "1900-01-01"))
                    end_date = datetime.fromisoformat(date_range.get("end_date", "2100-01-01"))
                    if not (start_date <= meeting.date <= end_date):
                        continue
                meetings_to_analyze.append((meeting_id, meeting))
            
            if not meetings_to_analyze:
                return [TextContent(
                    type="text",
                    text=f"No meetings found in the specified date range"
                )]
            
            # Build context for GPT - include meeting titles, participants, and available content
            meeting_contexts = []
            for meeting_id, meeting in meetings_to_analyze[:limit * 2]:  # Analyze more than limit to get better results
                context = {
                    "id": meeting_id,
                    "title": meeting.title,
                    "date": meeting.date.isoformat(),
                    "participants": meeting.participants
                }
                
                # Add document content if available
                if meeting_id in self.cache_data.documents:
                    doc = self.cache_data.documents[meeting_id]
                    if doc.content:
                        context["notes"] = doc.content[:2000]  # Limit to avoid token limits
                
                # Add transcript snippet if available
                if meeting_id in self.cache_data.transcripts:
                    transcript = self.cache_data.transcripts[meeting_id]
                    if transcript.content:
                        context["transcript"] = transcript.content[:2000]
                
                meeting_contexts.append(context)
            
            # Use GPT to analyze which meetings match the category
            prompt = f"""You are analyzing meeting records to find companies that match a specific category.

Category to find: {category}

For each meeting, determine if the company discussed matches this category. Consider:
- The company's product/service
- Their target market
- Their business model
- Industry/vertical
- Technology stack (if relevant)

Return a JSON array of meeting IDs that match, ordered by relevance. Only include meetings where you're confident the company matches the category.

Meeting data:
{json.dumps(meeting_contexts, indent=2, default=str)}

Return a JSON object with a "meeting_ids" array containing the matching meeting IDs, ordered by relevance.
Example: {{"meeting_ids": ["id1", "id2", "id3"]}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4o for best intelligence and accuracy
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes business meetings to categorize companies. Always return valid JSON with a 'meeting_ids' array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse GPT response
            result_text = response.choices[0].message.content
            try:
                result_data = json.loads(result_text)
                # GPT should return {"meeting_ids": [...]}
                matching_ids = result_data.get("meeting_ids", result_data.get("meetings", []))
                if not isinstance(matching_ids, list):
                    matching_ids = []
            except json.JSONDecodeError:
                # Fallback: try to extract IDs from text
                import re
                matching_ids = re.findall(r'["\']([a-f0-9-]{36})["\']', result_text)
            
            # Get meeting details for matches
            results = []
            for meeting_id in matching_ids[:limit]:
                if meeting_id in self.cache_data.meetings:
                    meeting = self.cache_data.meetings[meeting_id]
                    results.append(meeting)
            
            if not results:
                return [TextContent(
                    type="text",
                    text=f"No companies found matching '{category}' in the specified date range"
                )]
            
            # Format results
            output = [f"# Companies Matching: {category}\n\n"]
            output.append(f"Found {len(results)} company/companies:\n\n")
            
            for meeting in results:
                output.append(f"## {meeting.title}")
                output.append(f"**Date:** {self._format_local_time(meeting.date)}")
                output.append(f"**ID:** {meeting.id}")
                
                if meeting.participants:
                    output.append(f"**Participants:** {', '.join(meeting.participants)}")
                
                # Add notes/transcript preview if available
                if meeting.id in self.cache_data.documents:
                    doc = self.cache_data.documents[meeting.id]
                    if doc.content:
                        preview = doc.content[:300].replace('\n', ' ')
                        output.append(f"**Notes preview:** {preview}...")
                
                output.append("")
            
            return [TextContent(type="text", text="\n".join(output))]
            
        except Exception as e:
            sys.stderr.write(f"Error in intelligent category search: {e}\n")
            import traceback
            traceback.print_exc(file=sys.stderr)
            return [TextContent(
                type="text",
                text=f"Error performing intelligent search: {str(e)}"
            )]
    
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