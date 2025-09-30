"""
Tableau Metadata Normalization and Record Builder
Processes GraphQL metadata into database-ready records for the RWA Chatbot
"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def to_text_blob(title: str, desc: str, tags: List[str], fields: List[str], 
                project: str, owner: str, additional_text: str = "") -> str:
    """
    Create a searchable text blob from object metadata
    
    Args:
        title: Object title
        desc: Object description
        tags: List of tag names
        fields: List of field names
        project: Project name
        owner: Owner name
        additional_text: Any additional text to include
        
    Returns:
        Normalized text blob for search indexing
    """
    parts = [
        title or "",
        desc or "",
        " ".join(tags or []),
        " ".join(fields or []),
        project or "",
        owner or "",
        additional_text or ""
    ]
    
    # Join parts and clean up whitespace
    text = " \n ".join([p.strip() for p in parts if p])
    text = re.sub(r"\s+", " ", text)
    
    return text.lower()


def build_workbook_record(site_id: str, workbook: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a database record for a workbook
    
    Args:
        site_id: Tableau site ID
        workbook: Workbook metadata from GraphQL
        
    Returns:
        Database record dictionary
    """
    title = workbook.get("name", "")
    desc = workbook.get("description") or ""
    tags = [t.get("name", "") for t in (workbook.get("tags") or [])]
    project = workbook.get("projectName", "")
    owner = (workbook.get("owner") or {}).get("name", "")
    content_url = workbook.get("contentUrl", "")
    
    # Workbooks don't have fields, but we can include additional context
    additional_text = f"workbook {title}"
    
    record = {
        "site_id": site_id,
        "object_type": "workbook",
        "object_id": workbook.get("id", ""),
        "title": title,
        "description": desc,
        "tags": tags,
        "fields": [],  # Workbooks don't have fields
        "project_name": project,
        "owner": owner,
        "url": content_url,
        "text_blob": to_text_blob(title, desc, tags, [], project, owner, additional_text)
    }
    
    return record


def build_datasource_record(site_id: str, datasource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a database record for a datasource
    
    Args:
        site_id: Tableau site ID
        datasource: Datasource metadata from GraphQL
        
    Returns:
        Database record dictionary
    """
    title = datasource.get("name", "")
    desc = datasource.get("description") or ""
    tags = [t.get("name", "") for t in (datasource.get("tags") or [])]
    project = datasource.get("projectName", "")
    owner = (datasource.get("owner") or {}).get("name", "")
    content_url = datasource.get("contentUrl", "")
    
    # Extract field information
    fields = []
    field_details = []
    for field in datasource.get("fields", []):
        field_name = field.get("name", "")
        if field_name:
            fields.append(field_name)
            field_details.append({
                "name": field_name,
                "description": field.get("description", ""),
                "data_type": field.get("dataType", ""),
                "is_nullable": field.get("isNullable", False)
            })
    
    # Additional context for datasources
    additional_text = f"datasource {title} with {len(fields)} fields"
    
    record = {
        "site_id": site_id,
        "object_type": "datasource",
        "object_id": datasource.get("id", ""),
        "title": title,
        "description": desc,
        "tags": tags,
        "fields": fields,
        "project_name": project,
        "owner": owner,
        "url": content_url,
        "text_blob": to_text_blob(title, desc, tags, fields, project, owner, additional_text),
        "field_details": field_details  # Store detailed field information
    }
    
    return record


def build_view_record(site_id: str, view: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a database record for a view
    
    Args:
        site_id: Tableau site ID
        view: View metadata from GraphQL
        
    Returns:
        Database record dictionary
    """
    title = view.get("name", "")
    desc = view.get("description") or ""
    tags = [t.get("name", "") for t in (view.get("tags") or [])]
    
    # Extract workbook information
    workbook = view.get("workbook", {})
    project = workbook.get("projectName", "")
    workbook_name = workbook.get("name", "")
    
    # Extract owner information
    owner = (view.get("owner") or {}).get("name", "")
    
    # Extract field information from datasources
    field_groups = view.get("datasourceFields") or []
    fields = []
    datasource_info = []
    
    for ds_group in field_groups:
        ds_name = ds_group.get("name", "")
        ds_fields = []
        for field in ds_group.get("fields", []):
            field_name = field.get("name", "")
            if field_name:
                fields.append(field_name)
                ds_fields.append(field_name)
        
        if ds_name:
            datasource_info.append({
                "name": ds_name,
                "fields": ds_fields
            })
    
    content_url = view.get("contentUrl", "")
    sheet_type = view.get("sheetType", "")
    
    # Additional context for views
    additional_text = f"view {title} in workbook {workbook_name} type {sheet_type}"
    
    record = {
        "site_id": site_id,
        "object_type": "view",
        "object_id": view.get("id", ""),
        "title": title,
        "description": desc,
        "tags": tags,
        "fields": fields,
        "project_name": project,
        "owner": owner,
        "url": content_url,
        "text_blob": to_text_blob(title, desc, tags, fields, project, owner, additional_text),
        "workbook_name": workbook_name,
        "sheet_type": sheet_type,
        "datasource_info": datasource_info
    }
    
    return record


def normalize_metadata_records(site_id: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize all metadata records for a site
    
    Args:
        site_id: Tableau site ID
        metadata: Normalized metadata dictionary from GraphQL client
        
    Returns:
        List of database-ready records
    """
    records = []
    
    # Process workbooks
    for workbook in metadata.get("workbooks", []):
        try:
            record = build_workbook_record(site_id, workbook)
            records.append(record)
        except Exception as e:
            logger.error(f"Failed to build workbook record: {e}")
            continue
    
    # Process datasources
    for datasource in metadata.get("datasources", []):
        try:
            record = build_datasource_record(site_id, datasource)
            records.append(record)
        except Exception as e:
            logger.error(f"Failed to build datasource record: {e}")
            continue
    
    # Process views
    for view in metadata.get("views", []):
        try:
            record = build_view_record(site_id, view)
            records.append(record)
        except Exception as e:
            logger.error(f"Failed to build view record: {e}")
            continue
    
    logger.info(f"Normalized {len(records)} records for site {site_id}")
    return records


def build_deep_link_url(server_url: str, content_url: str, site_name: str, object_type: str) -> str:
    """
    Build a proper Tableau deep link URL for views and workbooks
    
    Args:
        server_url: Tableau server base URL
        content_url: Content URL from metadata
        site_name: Tableau site name
        object_type: Type of object (view, workbook, datasource)
        
    Returns:
        Properly formatted deep link URL
    """
    if not content_url:
        return ""
    
    # Ensure server URL doesn't end with slash
    server_url = server_url.rstrip("/")
    
    # Remove leading slash if present
    if content_url.startswith("/"):
        content_url = content_url[1:]
    
    # For views, create the proper deep link format
    if object_type == "view":
        # Extract workbook and sheet from content URL
        # Format: views/workbook-name/sheet-name
        parts = content_url.split("/")
        if len(parts) >= 3 and parts[0] == "views":
            workbook = parts[1]
            sheet = parts[2]
            deep_link = f"{server_url}/#/site/{site_name}/views/{workbook}/{sheet}?:showAppBanner=false&:origin=card"
            return deep_link
    
    # For workbooks, create workbook deep link
    elif object_type == "workbook":
        # Format: workbooks/workbook-name
        parts = content_url.split("/")
        if len(parts) >= 2 and parts[0] == "workbooks":
            workbook = parts[1]
            deep_link = f"{server_url}/#/site/{site_name}/workbooks/{workbook}?:showAppBanner=false&:origin=card"
            return deep_link
    
    # For datasources, create datasource deep link
    elif object_type == "datasource":
        # Format: datasources/datasource-name
        parts = content_url.split("/")
        if len(parts) >= 2 and parts[0] == "datasources":
            datasource = parts[1]
            deep_link = f"{server_url}/#/site/{site_name}/datasources/{datasource}?:showAppBanner=false&:origin=card"
            return deep_link
    
    # Fallback to simple URL construction
    return f"{server_url}/{content_url}"


def build_full_url(server_url: str, content_url: str) -> str:
    """
    Build a full URL from server URL and content URL (legacy method)
    
    Args:
        server_url: Tableau server base URL
        content_url: Content URL from metadata
        
    Returns:
        Full URL for the object
    """
    if not content_url:
        return ""
    
    # Remove leading slash if present
    if content_url.startswith("/"):
        content_url = content_url[1:]
    
    # Ensure server URL doesn't end with slash
    server_url = server_url.rstrip("/")
    
    return f"{server_url}/{content_url}"


def enhance_record_with_urls(record: Dict[str, Any], server_url: str, site_name: str) -> Dict[str, Any]:
    """
    Enhance a record with deep link URLs
    
    Args:
        record: Database record
        server_url: Tableau server base URL
        site_name: Tableau site name
        
    Returns:
        Enhanced record with deep link URL
    """
    if record.get("url"):
        object_type = record.get("object_type", "")
        record["deep_link_url"] = build_deep_link_url(server_url, record["url"], site_name, object_type)
        record["full_url"] = build_full_url(server_url, record["url"])  # Keep legacy URL too
    else:
        record["deep_link_url"] = ""
        record["full_url"] = ""
    
    return record


def get_search_priority(object_type: str) -> int:
    """
    Get search priority for different object types
    Higher numbers = higher priority in search results
    
    Args:
        object_type: Type of object (workbook, datasource, view)
        
    Returns:
        Priority score
    """
    priorities = {
        "view": 3,        # Views are most relevant for "where to find" queries
        "workbook": 2,    # Workbooks are second most relevant
        "datasource": 1   # Datasources are least relevant for end users
    }
    
    return priorities.get(object_type, 0)


def add_search_metadata(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add search-specific metadata to a record
    
    Args:
        record: Database record
        
    Returns:
        Enhanced record with search metadata
    """
    record["search_priority"] = get_search_priority(record.get("object_type", ""))
    record["text_length"] = len(record.get("text_blob", ""))
    record["field_count"] = len(record.get("fields", []))
    record["tag_count"] = len(record.get("tags", []))
    
    return record


def process_metadata_for_indexing(site_id: str, metadata: Dict[str, Any], 
                                server_url: str, site_name: str) -> List[Dict[str, Any]]:
    """
    Complete processing pipeline for metadata indexing
    
    Args:
        site_id: Tableau site ID
        metadata: Normalized metadata from GraphQL client
        server_url: Tableau server base URL
        site_name: Tableau site name for deep links
        
    Returns:
        List of fully processed records ready for database insertion
    """
    # Normalize records
    records = normalize_metadata_records(site_id, metadata)
    
    # Enhance with URLs and search metadata
    enhanced_records = []
    for record in records:
        try:
            # Add deep link URLs
            record = enhance_record_with_urls(record, server_url, site_name)
            
            # Add search metadata
            record = add_search_metadata(record)
            
            enhanced_records.append(record)
            
        except Exception as e:
            logger.error(f"Failed to enhance record {record.get('title', 'Unknown')}: {e}")
            continue
    
    logger.info(f"Processed {len(enhanced_records)} records for indexing")
    return enhanced_records
