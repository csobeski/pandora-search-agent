from google.adk.agents.llm_agent import Agent

import httpx

# Placeholder for your actual access token retrieval function
def get_pandora_access_token():
    # In a real app, this would involve OAuth flow with your credentials
    # For the capstone project, replace with a hardcoded test token:
    return "<replace with test token>"

# MAPPING: Map pandora_search_catalog's content_type arg to the Pandora GraphQL Type ID
# SF = Station Factory (often what you want when searching for a 'Station')
# ST = Station (a user's saved/active station)
# TR = Track
# AL = Album
# AR = Artist
CONTENT_TYPE_MAP = {
    'ARTIST': 'AR',
    'STATION': 'SF', # Searching for a Station Factory (a seedable station)
    'ALBUM': 'AL',
    'TRACK': 'TR',
    'PODCAST': 'PC'
}

def pandora_search_catalog(query: str, content_type: str) -> dict:
    """
    Searches the Pandora catalog for artists, stations, albums, tracks, or podcasts.

    Use this tool to discover new content based on a user's search query.
    The agent should infer the most relevant content_type (e.g., 'ARTIST', 'STATION', 'PODCAST')
    from the user's request.

    Args:
        query: The search term (e.g., "new alternative rock" or "podcast about space").
        content_type: The specific content type to search for. Must be one of:
                      'ARTIST', 'STATION', 'ALBUM', 'TRACK', or 'PODCAST'.

    Returns:
        A dictionary containing the search results (names, IDs, and descriptions),
        or an error message.
    """
    
    pandora_type_id = CONTENT_TYPE_MAP.get(content_type.upper())
    
    if not pandora_type_id:
        return {"error": f"Invalid content_type: {content_type}."}

    # 1. CONSTRUCT THE FULL, UN-PARAMETERIZED QUERY (Matching curl structure)
    graphql_query = f"""
        {{
            search(types: [{pandora_type_id}], query: \"{query}\", pagination: {{limit: 20}}) {{
                items {{
                    id
                    ... on Station {{
                        name
                        art {{
                            url(size: WIDTH_90)
                        }}
                        description
                    }}
                    ... on StationFactory {{
                        name
                        art {{
                            url(size: WIDTH_90)
                        }}
                        exampleArtists {{ name }}
                        description
                    }}
                    ... on Track {{
                        name
                        artist {{ name }}
                        album {{ name }}
                        url
                    }}
                    ... on Podcast {{
                        name
                        publisherName
                        url
                    }}
                    ... on Album {{
                        name
                        artist {{ name }}
                        releaseDate
                        tracks {{ name }}
                        trackCount
                        url
                    }}
                    ... on Artist {{
                        name
                        sortableName
                        url
                    }}
                }}
            }}
        }}
    """
    
    # 2. CONSTRUCT THE PAYLOAD (Data dictionary)
    data = {
        "operationName": None, # or omit this field
        "variables": {},       # Send empty variables
        "query": graphql_query.replace('\n', ' ').strip() # Clean up the query string
    }
    
    headers = {
        "Authorization": f"Bearer {get_pandora_access_token()}",
        "Content-Type": "application/json"
    }
    
    PANDORA_URL = "https://ce.pandora.com/api/v1/graphql/graphql"
    
    try:
        response = httpx.post(PANDORA_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status() 
        return response.json()
    except Exception as e:
        # This will now catch network/auth errors AND HTTP 4xx/5xx errors
        return {"error": f"Pandora API call failed: {e}", "response_text": response.text if 'response' in locals() else None}

CONTENT_DISCOVERY_INSTRUCTION = (
    "You are a Pandora Content Discovery Specialist. "
    "Your goal is to help the user find new music, stations, or podcasts. "
    "When a user asks to discover content, use the `pandora_search_catalog` tool. "
    "When choosing the `content_type` argument for the tool, use the following mapping: "
    "Search for **stations/genres** -> 'STATION'. "
    "Search for a **specific band or singer** -> 'ARTIST'. "
    "Search for a **specific song** -> 'TRACK'. "
    "Always present the results clearly."
)

content_discovery_agent = Agent(
    name="Content_Discovery_Agent",
    model="gemini-2.5-flash",
    description="An agent that discovers new content using the Pandora Search API.",
    instruction=CONTENT_DISCOVERY_INSTRUCTION,
    tools=[pandora_search_catalog]
)

root_agent = content_discovery_agent
