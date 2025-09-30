"""
Database writer module for RWA Chatbot Phase 1
Provides high-level functions for writing Tableau objects to the database
"""

import logging
from typing import List, Dict, Any
from .store import upsert_records, get_record_count, get_embedding_stats

logger = logging.getLogger(__name__)


def upsert_objects(objects: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Upsert Tableau objects into the database and return statistics
    
    Args:
        objects: List of Tableau object dictionaries to upsert
        
    Returns:
        Dictionary with statistics about the upsert operation
    """
    if not objects:
        logger.warning("No objects to upsert")
        return {
            "workbooks": 0,
            "datasources": 0,
            "views": 0,
            "total": 0,
            "errors": 0
        }
    
    # Count objects by type
    workbooks = sum(1 for obj in objects if obj.get("object_type") == "workbook")
    datasources = sum(1 for obj in objects if obj.get("object_type") == "datasource")
    views = sum(1 for obj in objects if obj.get("object_type") == "view")
    
    logger.info(f"Upserting {len(objects)} objects: {workbooks} workbooks, {datasources} datasources, {views} views")
    
    try:
        # Upsert all objects
        processed_count = upsert_records(objects)
        
        return {
            "workbooks": workbooks,
            "datasources": datasources,
            "views": views,
            "total": processed_count,
            "errors": len(objects) - processed_count
        }
        
    except Exception as e:
        logger.error(f"Error upserting objects: {e}")
        return {
            "workbooks": 0,
            "datasources": 0,
            "views": 0,
            "total": 0,
            "errors": len(objects)
        }


def get_database_stats(site_id: str = None) -> Dict[str, Any]:
    """
    Get comprehensive database statistics
    
    Args:
        site_id: Optional site ID to filter by
        
    Returns:
        Dictionary with database statistics
    """
    try:
        # Get record counts by type
        workbooks = get_record_count(site_id, "workbook")
        datasources = get_record_count(site_id, "datasource")
        views = get_record_count(site_id, "view")
        total = workbooks + datasources + views
        
        # Get embedding stats
        embedding_stats = get_embedding_stats()
        
        return {
            "workbooks": workbooks,
            "datasources": datasources,
            "views": views,
            "total": total,
            "embedding_stats": embedding_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {
            "workbooks": 0,
            "datasources": 0,
            "views": 0,
            "total": 0,
            "embedding_stats": {}
        }
