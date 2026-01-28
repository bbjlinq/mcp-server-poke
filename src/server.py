#!/usr/bin/env python3
import os
import requests
from fastmcp import FastMCP
from datetime import datetime

# Initialize MCP server
mcp = FastMCP("HubSpot MCP Server")

# Get HubSpot access token from environment
HUBSPOT_ACCESS_TOKEN = os.environ.get("HUBSPOT_ACCESS_TOKEN")
HUBSPOT_API_BASE = "https://api.hubapi.com"

@mcp.tool(description="Greet a user by name with a welcome message from the MCP server")
def greet(name: str) -> str:
    return f"Hello, {name}! Welcome to our HubSpot MCP server!"

@mcp.tool(description="Get information about the MCP server including name, version, environment, and Python version")
def get_server_info() -> dict:
    return {
        "server_name": "HubSpot MCP Server",
        "version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": os.sys.version.split()[0],
        "hubspot_connected": bool(HUBSPOT_ACCESS_TOKEN)
    }

@mcp.tool(description="Search HubSpot CRM for contacts, deals, companies, or other objects")
def search_hubspot(
    query: str,
    object_type: str = "contacts",
    limit: int = 10
) -> dict:
    """
    Search HubSpot CRM objects by text query.
    
    Args:
        query: Search term to find in records
        object_type: Type of object to search (contacts, deals, companies, tickets)
        limit: Maximum number of results to return (default: 10, max: 100)
    
    Returns:
        Dictionary with search results including total count and matching records
    """
    if not HUBSPOT_ACCESS_TOKEN:
        return {
            "error": "HubSpot access token not configured",
            "status": "error"
        }
    
    try:
        # Determine which property to search based on object type
        search_property = {
            "contacts": "email",
            "companies": "name",
            "deals": "dealname",
            "tickets": "subject"
        }.get(object_type, "name")
        
        # Determine which properties to return
        properties = {
            "contacts": ["firstname", "lastname", "email", "phone", "company"],
            "companies": ["name", "domain", "industry", "city"],
            "deals": ["dealname", "amount", "dealstage", "closedate", "pipeline", "hubspot_owner_id"],
            "tickets": ["subject", "content", "hs_pipeline_stage"]
        }.get(object_type, ["name"])
        
        # Build search request
        url = f"{HUBSPOT_API_BASE}/crm/v3/objects/{object_type}/search"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": search_property,
                            "operator": "CONTAINS_TOKEN",
                            "value": query
                        }
                    ]
                }
            ],
            "properties": properties,
            "limit": min(limit, 100)
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "status": "success",
            "object_type": object_type,
            "query": query,
            "total": data.get("total", 0),
            "results": data.get("results", [])
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "error": "Search failed",
            "message": str(e),
            "status": "error"
        }

@mcp.tool(description="Filter HubSpot deals by stage, pipeline, owner, or other properties")
def filter_deals(
    dealstage: str = None,
    pipeline: str = None,
    owner_id: str = None,
    limit: int = 100
) -> dict:
    """
    Filter HubSpot deals by specific properties.
    
    Args:
        dealstage: Deal stage to filter by (e.g., "54094855" for Proposal Sent)
        pipeline: Pipeline ID to filter by (e.g., "54094853" for Linq One)
        owner_id: Owner ID to filter by (e.g., "1944725253")
        limit: Maximum number of results to return (default: 100, max: 100)
    
    Returns:
        Dictionary with filtered deals
    """
    if not HUBSPOT_ACCESS_TOKEN:
        return {
            "error": "HubSpot access token not configured",
            "status": "error"
        }
    
    try:
        # Build filters
        filters = []
        
        if dealstage:
            filters.append({
                "propertyName": "dealstage",
                "operator": "EQ",
                "value": dealstage
            })
        
        if pipeline:
            filters.append({
                "propertyName": "pipeline",
                "operator": "EQ",
                "value": pipeline
            })
        
        if owner_id:
            filters.append({
                "propertyName": "hubspot_owner_id",
                "operator": "EQ",
                "value": owner_id
            })
        
        if not filters:
            return {
                "error": "At least one filter parameter is required (dealstage, pipeline, or owner_id)",
                "status": "error"
            }
        
        # Build search request
        url = f"{HUBSPOT_API_BASE}/crm/v3/objects/deals/search"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "filterGroups": [
                {
                    "filters": filters
                }
            ],
            "properties": ["dealname", "amount", "dealstage", "closedate", "pipeline", "hubspot_owner_id", "createdate"],
            "limit": min(limit, 100)
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "status": "success",
            "filters_applied": {
                "dealstage": dealstage,
                "pipeline": pipeline,
                "owner_id": owner_id
            },
            "total": data.get("total", 0),
            "results": data.get("results", [])
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "error": "Filter failed",
            "message": str(e),
            "status": "error"
        }

@mcp.tool(description="Get HubSpot owner information by searching for owners")
def search_owners(
    search_query: str = None,
    limit: int = 25
) -> dict:
    """
    Search for HubSpot owners (users who can own deals/contacts).
    
    Args:
        search_query: Optional search term to filter owners by name or email
        limit: Maximum number of results (default: 25, max: 100)
    
    Returns:
        Dictionary with owner information including IDs
    """
    if not HUBSPOT_ACCESS_TOKEN:
        return {
            "error": "HubSpot access token not configured",
            "status": "error"
        }
    
    try:
        url = f"{HUBSPOT_API_BASE}/crm/v3/owners/"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        params = {
            "limit": min(limit, 100)
        }
        
        if search_query:
            params["email"] = search_query
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "status": "success",
            "total": len(data.get("results", [])),
            "results": data.get("results", [])
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "error": "Owner search failed",
            "message": str(e),
            "status": "error"
        }

@mcp.tool(description="Get notes associated with a HubSpot contact")
def get_contact_notes(
    contact_id: str,
    include_timestamps: bool = True,
    limit: int = 10,
    search_text: str = None
) -> dict:
    """
    Retrieve notes associated with a contact record.
    
    Args:
        contact_id: Required HubSpot contact ID
        include_timestamps: Include creation dates (default: True)
        limit: Number of most recent notes to return (default: 10, max: 100)
        search_text: Optional filter for notes containing specific text
    
    Returns:
        Dictionary with array of note objects containing:
        - note_text: The actual note content
        - created_date: Timestamp when note was created (if include_timestamps=True)
        - author: Name/ID of note creator
        - note_type: Type of engagement
        - associated_deals: List of associated deal IDs
    """
    if not HUBSPOT_ACCESS_TOKEN:
        return {
            "error": "HubSpot access token not configured",
            "status": "error"
        }
    
    try:
        headers = {
            "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # First, verify the contact exists
        contact_url = f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{contact_id}"
        contact_response = requests.get(contact_url, headers=headers)
        if contact_response.status_code == 404:
            return {
                "error": f"Contact with ID {contact_id} does not exist",
                "status": "error"
            }
        contact_response.raise_for_status()
        
        # Get note associations for this contact using v4 associations API
        associations_url = f"{HUBSPOT_API_BASE}/crm/v4/objects/contacts/{contact_id}/associations/notes"
        assoc_params = {"limit": min(limit, 500)}
        
        assoc_response = requests.get(associations_url, headers=headers, params=assoc_params)
        assoc_response.raise_for_status()
        
        assoc_data = assoc_response.json()
        note_associations = assoc_data.get("results", [])
        
        # If no notes found, return gracefully
        if not note_associations:
            return {
                "status": "success",
                "contact_id": contact_id,
                "total_notes": 0,
                "notes": [],
                "message": "No notes found for this contact"
            }
        
        # Get the actual note IDs
        note_ids = [assoc.get("toObjectId") for assoc in note_associations]
        
        # Fetch the actual notes with their properties
        processed_notes = []
        
        for note_id in note_ids[:limit]:  # Respect the limit
            note_url = f"{HUBSPOT_API_BASE}/crm/v3/objects/notes/{note_id}"
            note_params = {
                "properties": "hs_note_body,hs_timestamp,hubspot_owner_id,hs_attachment_ids"
            }
            
            try:
                note_response = requests.get(note_url, headers=headers, params=note_params)
                note_response.raise_for_status()
                note_data = note_response.json()
                
                props = note_data.get("properties", {})
                note_text = props.get("hs_note_body", "")
                
                # Apply search filter if provided
                if search_text and search_text.lower() not in note_text.lower():
                    continue
                
                note_obj = {
                    "note_id": note_id,
                    "note_text": note_text,
                }
                
                if include_timestamps:
                    timestamp = props.get("hs_timestamp")
                    if timestamp:
                        try:
                            dt = datetime.fromtimestamp(int(timestamp) / 1000)
                            note_obj["created_date"] = dt.isoformat()
                        except:
                            note_obj["created_date"] = timestamp
                
                owner_id = props.get("hubspot_owner_id")
                if owner_id:
                    note_obj["author_id"] = owner_id
                
                processed_notes.append(note_obj)
                
            except requests.exceptions.RequestException:
                # Skip notes that fail to fetch
                continue
        
        # Sort by timestamp if available
        processed_notes.sort(
            key=lambda x: x.get("created_date", ""),
            reverse=True
        )
        
        return {
            "status": "success",
            "contact_id": contact_id,
            "total_notes": len(processed_notes),
            "notes": processed_notes
        }
        
    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get("message", error_message)
            except:
                pass
        
        return {
            "error": "Failed to retrieve contact notes",
            "message": error_message,
            "status": "error"
        }

@mcp.tool(description="Update, create, or get HubSpot CRM records")
def update_hubspot(
    action: str,
    object_type: str,
    object_id: str = None,
    properties: dict = None
) -> dict:
    """
    Perform actions on HubSpot CRM records.
    
    Args:
        action: Action to perform (update, create, get)
        object_type: Type of object (contacts, deals, companies, tickets)
        object_id: ID of the object (required for update and get)
        properties: Dictionary of properties to update/create
    
    Returns:
        Dictionary with action result
    """
    if not HUBSPOT_ACCESS_TOKEN:
        return {
            "error": "HubSpot access token not configured",
            "status": "error"
        }
    
    try:
        headers = {
            "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        if action == "update":
            if not object_id:
                return {"error": "object_id required for update", "status": "error"}
            url = f"{HUBSPOT_API_BASE}/crm/v3/objects/{object_type}/{object_id}"
            response = requests.patch(url, json={"properties": properties}, headers=headers)
            
        elif action == "create":
            url = f"{HUBSPOT_API_BASE}/crm/v3/objects/{object_type}"
            response = requests.post(url, json={"properties": properties}, headers=headers)
            
        elif action == "get":
            if not object_id:
                return {"error": "object_id required for get", "status": "error"}
            url = f"{HUBSPOT_API_BASE}/crm/v3/objects/{object_type}/{object_id}"
            response = requests.get(url, headers=headers)
            
        else:
            return {"error": f"Invalid action: {action}. Use: update, create, or get", "status": "error"}
        
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action,
            "object_type": object_type,
            "data": response.json()
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Action {action} failed",
            "message": str(e),
            "status": "error"
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Starting HubSpot FastMCP server on {host}:{port}")
    
    # Run with SSE transport for MCP integration compatibility
    mcp.run(
        transport="sse",
        host=host,
        port=port
    )
