#!/usr/bin/env python3
import os
import requests
from fastmcp import FastMCP

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
        dealstage: Deal stage to filter by (e.g., "Proposal Sent", "appointmentscheduled")
        pipeline: Pipeline name or ID to filter by (e.g., "Linq One", "default")
        owner_id: Owner ID to filter by
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
    
    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True
    )
