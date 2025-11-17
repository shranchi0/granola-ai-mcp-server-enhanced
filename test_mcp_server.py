#!/usr/bin/env python3
"""Test the MCP server to verify date parsing works."""

import asyncio
import json
from granola_mcp_server.server import GranolaMCPServer

async def test_search():
    """Test the search functionality."""
    server = GranolaMCPServer()
    await server._ensure_cache_loaded()
    
    print("Testing date query parsing...")
    print("=" * 60)
    
    # Test various date queries
    test_queries = [
        "this week",
        "last week", 
        "November 2025",
        "today",
        "yesterday"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        date_range = server._parse_date_query(query)
        if date_range:
            print(f"  Date range: {date_range[0]} to {date_range[1]}")
            
            # Count meetings in range
            count = 0
            for meeting_id, meeting in server.cache_data.meetings.items():
                local_date = server._convert_to_local_time(meeting.date)
                if date_range[0] <= local_date <= date_range[1]:
                    count += 1
            
            print(f"  Meetings found: {count}")
            
            # Actually run the search
            results = await server._search_meetings(query, limit=5)
            if results:
                print(f"  Search result preview:")
                preview = results[0].text[:300]
                print(f"    {preview}...")
        else:
            print(f"  No date range parsed (will use text search)")
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_search())

