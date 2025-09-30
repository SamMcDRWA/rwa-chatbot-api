"""
Database storage module for RWA Chatbot Phase 1
Handles upsert operations for Tableau object records
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def get_engine():
    """Create database engine from environment variables"""
    # Use DATABASE_URL if available, otherwise fall back to individual parameters
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return create_engine(database_url, future=True)
    else:
        # Get individual parameters with proper validation
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT', '5432')  # Default to 5432 if not set
        db_name = os.getenv('DB_NAME')
        
        # Validate required parameters
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Missing required database environment variables")
        
        url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        return create_engine(url, future=True)


# Upsert SQL for inserting/updating records
UPSERT_SQL = text("""
INSERT INTO chatbot.objects
(site_id, object_type, object_id, title, description, tags, fields, project_name, owner, url, text_blob, updated_at)
VALUES (:site_id, :object_type, :object_id, :title, :description, :tags, :fields, :project_name, :owner, :url, :text_blob, now())
ON CONFLICT (site_id, object_type, object_id)
DO UPDATE SET 
    title=EXCLUDED.title, 
    description=EXCLUDED.description, 
    tags=EXCLUDED.tags,
    fields=EXCLUDED.fields, 
    project_name=EXCLUDED.project_name, 
    owner=EXCLUDED.owner,
    url=EXCLUDED.url, 
    text_blob=EXCLUDED.text_blob, 
    updated_at=now();
""")


def upsert_records(records: List[Dict[str, Any]]) -> int:
    """
    Upsert records into the database
    
    Args:
        records: List of record dictionaries to upsert
        
    Returns:
        Number of records processed
    """
    if not records:
        logger.warning("No records to upsert")
        return 0
    
    engine = get_engine()
    processed_count = 0
    
    try:
        with engine.begin() as conn:
            for record in records:
                try:
                    # Prepare record data
                    record_data = {
                        "site_id": record.get("site_id"),
                        "object_type": record.get("object_type"),
                        "object_id": record.get("object_id"),
                        "title": record.get("title"),
                        "description": record.get("description"),
                        "tags": record.get("tags") or [],
                        "fields": record.get("fields") or [],
                        "project_name": record.get("project_name"),
                        "owner": record.get("owner"),
                        "url": record.get("url"),
                        "text_blob": record.get("text_blob")
                    }
                    
                    # Execute upsert
                    conn.execute(UPSERT_SQL, record_data)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to upsert record {record.get('title', 'Unknown')}: {e}")
                    continue
        
        logger.info(f"Successfully upserted {processed_count} records")
        return processed_count
        
    except SQLAlchemyError as e:
        logger.error(f"Database error during upsert: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upsert: {e}")
        raise


def upsert_records_batch(records: List[Dict[str, Any]], batch_size: int = 100) -> int:
    """
    Upsert records in batches for better performance
    
    Args:
        records: List of record dictionaries to upsert
        batch_size: Number of records to process per batch
        
    Returns:
        Number of records processed
    """
    if not records:
        logger.warning("No records to upsert")
        return 0
    
    total_processed = 0
    total_records = len(records)
    
    logger.info(f"Starting batch upsert of {total_records} records in batches of {batch_size}")
    
    for i in range(0, total_records, batch_size):
        batch = records[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_records + batch_size - 1) // batch_size
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} records)")
        
        try:
            processed = upsert_records(batch)
            total_processed += processed
            logger.info(f"Batch {batch_num} completed: {processed} records processed")
            
        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            continue
    
    logger.info(f"Batch upsert completed: {total_processed}/{total_records} records processed")
    return total_processed


def get_record_count(site_id: str = None, object_type: str = None) -> int:
    """
    Get count of records in the database
    
    Args:
        site_id: Optional site ID to filter by
        object_type: Optional object type to filter by
        
    Returns:
        Number of records matching criteria
    """
    engine = get_engine()
    
    query = "SELECT COUNT(*) FROM chatbot.objects WHERE 1=1"
    params = {}
    
    if site_id:
        query += " AND site_id = :site_id"
        params["site_id"] = site_id
    
    if object_type:
        query += " AND object_type = :object_type"
        params["object_type"] = object_type
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text(query), params).fetchone()
            return result[0] if result else 0
            
    except SQLAlchemyError as e:
        logger.error(f"Database error getting record count: {e}")
        raise


def get_records_by_type(site_id: str, object_type: str) -> List[Dict[str, Any]]:
    """
    Get records by site and object type
    
    Args:
        site_id: Site ID to filter by
        object_type: Object type to filter by
        
    Returns:
        List of record dictionaries
    """
    engine = get_engine()
    
    query = text("""
        SELECT * FROM chatbot.objects 
        WHERE site_id = :site_id AND object_type = :object_type
        ORDER BY updated_at DESC
    """)
    
    try:
        with engine.begin() as conn:
            result = conn.execute(query, {
                "site_id": site_id,
                "object_type": object_type
            }).fetchall()
            
            # Convert to list of dictionaries
            records = []
            for row in result:
                record = dict(row._mapping)
                records.append(record)
            
            return records
            
    except SQLAlchemyError as e:
        logger.error(f"Database error getting records: {e}")
        raise


def delete_records(site_id: str, object_type: str = None) -> int:
    """
    Delete records from the database
    
    Args:
        site_id: Site ID to filter by
        object_type: Optional object type to filter by
        
    Returns:
        Number of records deleted
    """
    engine = get_engine()
    
    query = "DELETE FROM chatbot.objects WHERE site_id = :site_id"
    params = {"site_id": site_id}
    
    if object_type:
        query += " AND object_type = :object_type"
        params["object_type"] = object_type
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text(query), params)
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} records for site {site_id}")
            return deleted_count
            
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting records: {e}")
        raise


def get_embedding_stats() -> Dict[str, Any]:
    """
    Get statistics about embeddings in the database
    
    Returns:
        Dictionary with embedding statistics
    """
    engine = get_engine()
    
    query = text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(embedding) as records_with_embeddings,
            COUNT(*) - COUNT(embedding) as records_without_embeddings
        FROM chatbot.objects
    """)
    
    try:
        with engine.begin() as conn:
            result = conn.execute(query).fetchone()
            
            if result:
                return {
                    "total_records": result[0],
                    "records_with_embeddings": result[1],
                    "records_without_embeddings": result[2],
                    "embedding_percentage": (result[1] / result[0] * 100) if result[0] > 0 else 0
                }
            else:
                return {
                    "total_records": 0,
                    "records_with_embeddings": 0,
                    "records_without_embeddings": 0,
                    "embedding_percentage": 0
                }
                
    except SQLAlchemyError as e:
        logger.error(f"Database error getting embedding stats: {e}")
        raise
