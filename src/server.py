#!/usr/bin/env python3
import os
import requests
from fastmcp import FastMCP
from datetime import datetime

# Initialize MCP server with SSE transport for Poke compatibility
mcp = FastMCP("HubSpot MCP Server")

# Get HubSpot access token from environment
HUBSPOT_ACCESS_TOKEN = os.environ.get("HUBSPOT_ACCESS_TOKEN")
HUBSPOT_API_BASE = "https://api.hubapi.com"

def get_headers():
    """Get authorization headers for HubSpot API calls."""
    return {
        "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }


# =============================================================================
# DEPLOY 1: Pipeline & Stage Mapping
# =============================================================================

@mcp.tool()
def get_pipelines() -> dict:
    """
    Get all deal pipelines and stages with human-readable names.
    Returns mapping of numeric IDs to display names for both pipelines and deal stages.
    Use this to convert IDs like '241882253' to names like 'Purchase Order Sent'.
    """
    try:
        result = {
            "pipelines": {},
            "stages": {}
        }
        
        # Get pipeline property (contains all pipeline options)
        url = f"{HUBSPOT_API_BASE}/crm/v3/properties/deals/pipeline"
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            data = response.json()
            for option in data.get("options", []):
                result["pipelines"][option["value"]] = option["label"]
        
        # Get dealstage property (contains all stage options)
        url = f"{HUBSPOT_API_BASE}/crm/v3/properties/deals/dealstage"
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            data = response.json()
            for option in data.get("options", []):
                result["stages"][option["value"]] = option["label"]
        
        return result
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# DEPLOY 2: Deal Associations (Contacts, Companies, Line Items)
# =============================================================================

@mcp.tool()
def get_deal_contacts(deal_id: str) -> dict:
    """
    Get all contacts associated with a specific deal.
    Returns contact details including name, email, phone, and job title.
    
    Args:
        deal_id: The HubSpot deal ID (e.g., '54956811307')
    """
    try:
        # First get associated contact IDs using v4 associations API
        url = f"{HUBSPOT_API_BASE}/crm/v4/objects/deals/{deal_id}/associations/contacts"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code != 200:
            return {"error": f"Failed to get associations: {response.text}"}
        
        associations = response.json().get("results", [])
        if not associations:
            return {"contacts": [], "message": "No contacts associated with this deal"}
        
        # Get contact details for each associated contact
        contacts = []
        for assoc in associations:
            contact_id = assoc.get("toObjectId")
            if contact_id:
                contact_url = f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{contact_id}"
                params = {"properties": "firstname,lastname,email,phone,jobtitle,company"}
                contact_response = requests.get(contact_url, headers=get_headers(), params=params)
                if contact_response.status_code == 200:
                    contact_data = contact_response.json()
                    contacts.append({
                        "id": contact_id,
                        "properties": contact_data.get("properties", {})
                    })
        
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_deal_companies(deal_id: str) -> dict:
    """
    Get all companies associated with a specific deal.
    Returns company details including name, domain, industry, and employee count.
    
    Args:
        deal_id: The HubSpot deal ID (e.g., '54956811307')
    """
    try:
        # Get associated company IDs using v4 associations API
        url = f"{HUBSPOT_API_BASE}/crm/v4/objects/deals/{deal_id}/associations/companies"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code != 200:
            return {"error": f"Failed to get associations: {response.text}"}
        
        associations = response.json().get("results", [])
        if not associations:
            return {"companies": [], "message": "No companies associated with this deal"}
        
        # Get company details for each associated company
        companies = []
        for assoc in associations:
            company_id = assoc.get("toObjectId")
            if company_id:
                company_url = f"{HUBSPOT_API_BASE}/crm/v3/objects/companies/{company_id}"
                params = {"properties": "name,domain,industry,numberofemployees,city,state,country"}
                company_response = requests.get(company_url, headers=get_headers(), params=params)
                if company_response.status_code == 200:
                    company_data = company_response.json()
                    companies.append({
                        "id": company_id,
                        "properties": company_data.get("properties", {})
                    })
        
        return {"companies": companies, "count": len(companies)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_deal_line_items(deal_id: str) -> dict:
    """
    Get all line items (products) associated with a specific deal.
    Returns product details including name, quantity, price, and amount.
    Use this to see what's included in a deal's total amount.
    
    Args:
        deal_id: The HubSpot deal ID (e.g., '54956811307')
    """
    try:
        # Get associated line item IDs using v4 associations API
        url = f"{HUBSPOT_API_BASE}/crm/v4/objects/deals/{deal_id}/associations/line_items"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code != 200:
            return {"error": f"Failed to get associations: {response.text}"}
        
        associations = response.json().get("results", [])
        if not associations:
            return {"line_items": [], "message": "No line items associated with this deal"}
        
        # Get line item details for each associated item
        line_items = []
        total_amount = 0
        for assoc in associations:
            item_id = assoc.get("toObjectId")
            if item_id:
                item_url = f"{HUBSPOT_API_BASE}/crm/v3/objects/line_items/{item_id}"
                params = {"properties": "name,quantity,price,amount,hs_product_id,description,hs_recurring_billing_period"}
                item_response = requests.get(item_url, headers=get_headers(), params=params)
                if item_response.status_code == 200:
                    item_data = item_response.json()
                    props = item_data.get("properties", {})
                    line_items.append({
                        "id": item_id,
                        "properties": props
                    })
                    if props.get("amount"):
                        total_amount += float(props["amount"])
        
        return {
            "line_items": line_items, 
            "count": len(line_items),
            "total_amount": total_amount
        }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# DEPLOY 3: History & Activity (Notes, Stage History, Emails)
# =============================================================================

@mcp.tool()
def get_deal_notes(deal_id: str) -> dict:
    """
    Get all notes associated with a specific deal.
    Returns note content, timestamp, and owner information.
    Use this to see the activity history and context on deal progression.
    
    Args:
        deal_id: The HubSpot deal ID (e.g., '54956811307')
    """
    try:
        # Get associated note IDs using v4 associations API
        url = f"{HUBSPOT_API_BASE}/crm/v4/objects/deals/{deal_id}/associations/notes"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code != 200:
            return {"error": f"Failed to get associations: {response.text}"}
        
        associations = response.json().get("results", [])
        if not associations:
            return {"notes": [], "message": "No notes associated with this deal"}
        
        # Get note details for each associated note
        notes = []
        for assoc in associations:
            note_id = assoc.get("toObjectId")
            if note_id:
                note_url = f"{HUBSPOT_API_BASE}/crm/v3/objects/notes/{note_id}"
                params = {"properties": "hs_note_body,hs_timestamp,hubspot_owner_id,hs_attachment_ids"}
                note_response = requests.get(note_url, headers=get_headers(), params=params)
                if note_response.status_code == 200:
                    note_data = note_response.json()
                    notes.append({
                        "id": note_id,
                        "properties": note_data.get("properties", {})
                    })
        
        # Sort by timestamp descending (most recent first)
        notes.sort(key=lambda x: x.get("properties", {}).get("hs_timestamp", ""), reverse=True)
        
        return {"notes": notes, "count": len(notes)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_deal_stage_history(deal_id: str) -> dict:
    """
    Get the stage history for a specific deal showing when it moved between stages.
    Returns timeline of stage changes with timestamps.
    
    Args:
        deal_id: The HubSpot deal ID (e.g., '54956811307')
    """
    try:
        # Use propertiesWithHistory to get stage change history
        url = f"{HUBSPOT_API_BASE}/crm/v3/objects/deals/{deal_id}"
        params = {
            "properties": "dealname,dealstage,pipeline",
            "propertiesWithHistory": "dealstage"
        }
        response = requests.get(url, headers=get_headers(), params=params)
        
        if response.status_code != 200:
            return {"error": f"Failed to get deal: {response.text}"}
        
        data = response.json()
        properties = data.get("properties", {})
        properties_with_history = data.get("propertiesWithHistory", {})
        
        stage_history = []
        if "dealstage" in properties_with_history:
            for entry in properties_with_history["dealstage"]:
                stage_history.append({
                    "stage_id": entry.get("value"),
                    "timestamp": entry.get("timestamp"),
                    "source": entry.get("sourceType")
                })
        
        # Sort by timestamp ascending (oldest first) to show progression
        stage_history.sort(key=lambda x: x.get("timestamp", ""))
        
        return {
            "deal_id": deal_id,
            "deal_name": properties.get("dealname"),
            "current_stage": properties.get("dealstage"),
            "pipeline": properties.get("pipeline"),
            "stage_history": stage_history,
            "total_stage_changes": len(stage_history)
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_deal_emails(deal_id: str) -> dict:
    """
    Get all emails associated with a specific deal.
    Returns email subject, body preview, sender, recipients, and timestamp.
    Use this to see communication history linked to a deal.
    
    Args:
        deal_id: The HubSpot deal ID (e.g., '54956811307')
    """
    try:
        # Get associated email IDs using v4 associations API
        url = f"{HUBSPOT_API_BASE}/crm/v4/objects/deals/{deal_id}/associations/emails"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code != 200:
            return {"error": f"Failed to get associations: {response.text}"}
        
        associations = response.json().get("results", [])
        if not associations:
            return {"emails": [], "message": "No emails associated with this deal"}
        
        # Get email details for each associated email
        emails = []
        for assoc in associations:
            email_id = assoc.get("toObjectId")
            if email_id:
                email_url = f"{HUBSPOT_API_BASE}/crm/v3/objects/emails/{email_id}"
                params = {"properties": "hs_email_subject,hs_email_text,hs_email_direction,hs_timestamp,hs_email_sender_email,hs_email_to_email"}
                email_response = requests.get(email_url, headers=get_headers(), params=params)
                if email_response.status_code == 200:
                    email_data = email_response.json()
                    emails.append({
                        "id": email_id,
                        "properties": email_data.get("properties", {})
                    })
        
        # Sort by timestamp descending (most recent first)
        emails.sort(key=lambda x: x.get("properties", {}).get("hs_timestamp", ""), reverse=True)
        
        return {"emails": emails, "count": len(emails)}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# EXISTING FUNCTIONS (with fixes applied)
# =============================================================================

@mcp.tool()
def search_hubspot(query: str, object_type: str = "contacts") -> dict:
    """
    Search HubSpot for contacts, companies, or deals by name/email.
    
    Args:
        query: Search term (name, email, company name, deal name)
        object_type: Type of object to search - 'contacts', 'companies', or 'deals'
    """
    try:
        url = f"{HUBSPOT_API_BASE}/crm/v3/objects/{object_type}/search"
        payload = {
            "query": query,
            "limit": 10,
            "properties": ["firstname", "lastname", "email", "phone", "company"] if object_type == "contacts"
                else ["name", "domain", "industry"] if object_type == "companies"
                else ["dealname", "amount", "dealstage", "pipeline", "closedate"]
        }
        response = requests.post(url, headers=get_headers(), json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def filter_deals(
    pipeline: str = None,
    dealstage: str = None,
    hubspot_owner_id: str = None,
    min_amount: float = None,
    max_amount: float = None,
    limit: int = 50
) -> dict:
    """
    Filter deals by pipeline, stage, owner, and/or amount range.
    All parameters are optional - only provided filters will be applied.
    
    IMPORTANT: Use numeric IDs for pipeline, dealstage, and hubspot_owner_id.
    Call get_pipelines() first to get the ID-to-name mappings.
    Call search_owners() to get owner IDs.
    
    Args:
        pipeline: Pipeline ID (e.g., '141575188' for 'Linq One')
        dealstage: Deal stage ID (e.g., '241882253' for 'Purchase Order Sent')
        hubspot_owner_id: Owner ID (e.g., '76301235' for 'Benjamin Johnson')
        min_amount: Minimum deal amount
        max_amount: Maximum deal amount
        limit: Maximum number of results (default 50)
    """
    try:
        url = f"{HUBSPOT_API_BASE}/crm/v3/objects/deals/search"
        
        # Build filters only for provided parameters
        filters = []
        
        if pipeline is not None and str(pipeline).strip():
            filters.append({
                "propertyName": "pipeline",
                "operator": "EQ",
                "value": str(pipeline)
            })
        
        if dealstage is not None and str(dealstage).strip():
            filters.append({
                "propertyName": "dealstage",
                "operator": "EQ",
                "value": str(dealstage)
            })
        
        if hubspot_owner_id is not None and str(hubspot_owner_id).strip():
            filters.append({
                "propertyName": "hubspot_owner_id",
                "operator": "EQ",
                "value": str(hubspot_owner_id)
            })
        
        if min_amount is not None:
            filters.append({
                "propertyName": "amount",
                "operator": "GTE",
                "value": str(min_amount)
            })
        
        if max_amount is not None:
            filters.append({
                "propertyName": "amount",
                "operator": "LTE",
                "value": str(max_amount)
            })
        
        payload = {
            "limit": limit,
            "properties": ["dealname", "amount", "dealstage", "pipeline", "closedate", "hubspot_owner_id"]
        }
        
        # Only add filterGroups if we have filters
        if filters:
            payload["filterGroups"] = [{"filters": filters}]
        
        response = requests.post(url, headers=get_headers(), json=payload)
        result = response.json()
        
        # Add total count for clarity
        if "total" in result:
            result["message"] = f"Found {result['total']} deals matching filters"
        
        return result
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_owners(query: str = None) -> dict:
    """
    Search for HubSpot owners (users who can be assigned to records).
    Returns owner IDs needed for filtering deals by owner.
    
    Args:
        query: Optional search term to filter owners by name or email.
               If not provided, returns all owners.
    """
    try:
        url = f"{HUBSPOT_API_BASE}/crm/v3/owners"
        params = {"limit": 100}
        if query:
            params["email"] = query
        
        response = requests.get(url, headers=get_headers(), params=params)
        data = response.json()
        
        owners = []
        for owner in data.get("results", []):
            owner_name = f"{owner.get('firstName', '')} {owner.get('lastName', '')}".strip()
            # Filter by query if provided (case-insensitive search in name or email)
            if query:
                query_lower = query.lower()
                if query_lower not in owner_name.lower() and query_lower not in owner.get("email", "").lower():
                    continue
            
            owners.append({
                "id": owner.get("id"),
                "name": owner_name,
                "email": owner.get("email"),
                "active": not owner.get("archived", False)
            })
        
        return {"owners": owners, "count": len(owners)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_contact_notes(contact_id: str) -> dict:
    """
    Get all notes associated with a specific contact.
    Uses the v4 associations API to find linked notes.
    
    Args:
        contact_id: The HubSpot contact ID
    """
    try:
        # Get associated note IDs using v4 associations API
        url = f"{HUBSPOT_API_BASE}/crm/v4/objects/contacts/{contact_id}/associations/notes"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code != 200:
            return {"error": f"Failed to get associations: {response.text}"}
        
        associations = response.json().get("results", [])
        if not associations:
            return {"notes": [], "message": "No notes associated with this contact"}
        
        # Get note details for each associated note
        notes = []
        for assoc in associations:
            note_id = assoc.get("toObjectId")
            if note_id:
                note_url = f"{HUBSPOT_API_BASE}/crm/v3/objects/notes/{note_id}"
                params = {"properties": "hs_note_body,hs_timestamp,hubspot_owner_id"}
                note_response = requests.get(note_url, headers=get_headers(), params=params)
                if note_response.status_code == 200:
                    note_data = note_response.json()
                    notes.append({
                        "id": note_id,
                        "properties": note_data.get("properties", {})
                    })
        
        # Sort by timestamp descending
        notes.sort(key=lambda x: x.get("properties", {}).get("hs_timestamp", ""), reverse=True)
        
        return {"notes": notes, "count": len(notes)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def update_hubspot(
    object_type: str,
    object_id: str,
    properties: dict
) -> dict:
    """
    Update a HubSpot record (contact, company, or deal).
    
    Args:
        object_type: Type of object - 'contacts', 'companies', or 'deals'
        object_id: The HubSpot object ID to update
        properties: Dictionary of properties to update (e.g., {'dealstage': '241882256'})
    
    Example - Move deal to Closed Won:
        update_hubspot('deals', '12345', {'dealstage': '241882256'})
    """
    try:
        url = f"{HUBSPOT_API_BASE}/crm/v3/objects/{object_type}/{object_id}"
        payload = {"properties": properties}
        response = requests.patch(url, headers=get_headers(), json=payload)
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": f"Successfully updated {object_type} {object_id}",
                "updated_properties": properties,
                "result": response.json()
            }
        else:
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Health Check & Server Startup
# =============================================================================

@mcp.tool()
def health_check() -> dict:
    """Check if the HubSpot connection is working."""
    try:
        url = f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts"
        params = {"limit": 1}
        response = requests.get(url, headers=get_headers(), params=params)
        return {
            "status": "connected" if response.status_code == 200 else "error",
            "hubspot_api": response.status_code == 200,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
