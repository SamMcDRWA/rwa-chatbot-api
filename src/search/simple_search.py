"""
Simple search module for RWA Adele
Provides basic text-based search without complex vector operations
"""

import os
import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SimpleSearch:
    """Simple text-based search for Tableau content"""
    
    def __init__(self):
        """Initialize the search engine"""
        self.engine = self._get_engine()
        logger.info("Simple search engine initialized")
    
    def _get_engine(self):
        """Get database engine"""
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return create_engine(database_url, future=True)
        else:
            # Fallback to individual parameters
            url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}" \
                  f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            return create_engine(url, future=True)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract meaningful keywords from a search query
        
        Args:
            query: Original search query
            
        Returns:
            List of meaningful keywords
        """
        import re
        
        # Convert to lowercase
        query = query.lower()
        
        # Remove common stop words
        stop_words = {
            'where', 'can', 'i', 'find', 'info', 'about', 'me', 'show', 'all', 
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'what', 'when', 'why', 'how'
        }
        
        # Extract words (alphanumeric characters and some special chars)
        words = re.findall(r'\b\w+\b', query)
        
        # Filter out stop words and short words
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # If no keywords found, use the original query
        if not keywords:
            keywords = [query]
        
        logger.info(f"Extracted keywords from '{query}': {keywords}")
        return keywords
    
    def _build_tableau_url(self, content_url: str, object_type: str) -> str:
        """
        Build a proper Tableau deep link URL
        
        Args:
            content_url: Content URL from database
            object_type: Type of object (workbook, view, datasource)
            
        Returns:
            Properly formatted Tableau deep link URL
        """
        if not content_url:
            return ""
        
        # Get Tableau server configuration from environment
        server_url = os.getenv('TABLEAU_SERVER_URL', 'https://dr.realworldretail.com')
        site_name = os.getenv('TABLEAU_SITE_NAME', 'EoinTest')
        
        # Ensure server URL doesn't end with slash
        server_url = server_url.rstrip("/")
        
        # Workbook-specific URL mappings for known workbooks
        workbook_urls = {
            'StoreCountByGroupDivision': f"{server_url}/#/site/{site_name}/views/StoreCountByGroupDivision/Sheet1?:iid=1"
        }
        
        # For workbooks, create view deep link (point to the first view/sheet)
        if object_type == "workbook":
            # Check if we have a specific URL mapping for this workbook
            workbook_name = content_url
            if content_url.startswith("workbooks/"):
                parts = content_url.split("/")
                if len(parts) >= 2:
                    workbook_name = parts[1]
            
            # Use specific URL if available, otherwise use generic format
            if workbook_name in workbook_urls:
                return workbook_urls[workbook_name]
            else:
                # Generic format for unknown workbooks
                deep_link = f"{server_url}/#/site/{site_name}/views/{workbook_name}/Sheet1?:iid=1"
                return deep_link
        
        # For views, create view deep link
        elif object_type == "view":
            if not content_url.startswith("views/"):
                view_name = content_url
                deep_link = f"{server_url}/#/site/{site_name}/views/{view_name}?:showAppBanner=false&:origin=card"
            else:
                # Extract workbook and sheet from views/workbook-name/sheet-name format
                parts = content_url.split("/")
                if len(parts) >= 3:
                    workbook_name = parts[1]
                    sheet_name = parts[2]
                    deep_link = f"{server_url}/#/site/{site_name}/views/{workbook_name}/{sheet_name}?:showAppBanner=false&:origin=card"
                else:
                    deep_link = f"{server_url}/#/site/{site_name}/views/{content_url}?:showAppBanner=false&:origin=card"
            return deep_link
        
        # For datasources, create datasource deep link
        elif object_type == "datasource":
            if not content_url.startswith("datasources/"):
                datasource_name = content_url
                deep_link = f"{server_url}/#/site/{site_name}/datasources/{datasource_name}?:showAppBanner=false&:origin=card"
            else:
                # Extract datasource name from datasources/datasource-name format
                parts = content_url.split("/")
                if len(parts) >= 2:
                    datasource_name = parts[1]
                    deep_link = f"{server_url}/#/site/{site_name}/datasources/{datasource_name}?:showAppBanner=false&:origin=card"
                else:
                    deep_link = f"{server_url}/#/site/{site_name}/datasources/{content_url}?:showAppBanner=false&:origin=card"
            return deep_link
        
        # Fallback to simple URL construction
        return f"{server_url}/{content_url}"
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for Tableau content using intelligent text matching
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching objects
        """
        try:
            with self.engine.begin() as conn:
                # Extract meaningful keywords from the query
                keywords = self._extract_keywords(query)
                
                # Build search conditions for each keyword
                search_conditions = []
                params = {"limit": limit}
                
                for i, keyword in enumerate(keywords):
                    param_name = f"keyword_{i}"
                    search_conditions.append(f"""
                        (title ILIKE :{param_name} OR 
                         description ILIKE :{param_name} OR 
                         text_blob ILIKE :{param_name} OR
                         project_name ILIKE :{param_name})
                    """)
                    params[param_name] = f"%{keyword}%"
                
                # Combine conditions with OR
                where_clause = " OR ".join(search_conditions) if search_conditions else "1=0"
                
                search_query = text(f"""
                    SELECT 
                        id, site_id, object_type, object_id, title, description,
                        tags, fields, project_name, owner, url, text_blob
                    FROM chatbot.objects 
                    WHERE {where_clause}
                    ORDER BY 
                        CASE 
                            WHEN title ILIKE :keyword_0 THEN 1
                            WHEN description ILIKE :keyword_0 THEN 2
                            WHEN text_blob ILIKE :keyword_0 THEN 3
                            ELSE 4
                        END,
                        title
                    LIMIT :limit
                """)
                
                result = conn.execute(search_query, params).fetchall()
                
                # Convert to list of dictionaries
                results = []
                for row in result:
                    obj = {
                        "id": row.id,
                        "site_id": row.site_id,
                        "object_type": row.object_type,
                        "object_id": row.object_id,
                        "title": row.title,
                        "description": row.description or "",
                        "tags": row.tags or [],
                        "fields": row.fields or [],
                        "project_name": row.project_name,
                        "owner": row.owner,
                        "url": self._build_tableau_url(row.url, row.object_type),
                        "text_blob": row.text_blob
                    }
                    results.append(obj)
                
                logger.info(f"Found {len(results)} results for query: {query}")
                return results
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def search_by_type(self, query: str, object_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for specific object type"""
        try:
            with self.engine.begin() as conn:
                search_query = text("""
                    SELECT 
                        id, site_id, object_type, object_id, title, description,
                        tags, fields, project_name, owner, url, text_blob
                    FROM chatbot.objects 
                    WHERE object_type = :object_type AND (
                        title ILIKE :query OR 
                        description ILIKE :query OR 
                        text_blob ILIKE :query OR
                        project_name ILIKE :query
                    )
                    ORDER BY title
                    LIMIT :limit
                """)
                
                search_term = f"%{query}%"
                
                result = conn.execute(search_query, {
                    "query": search_term,
                    "object_type": object_type,
                    "limit": limit
                }).fetchall()
                
                results = []
                for row in result:
                    obj = {
                        "id": row.id,
                        "site_id": row.site_id,
                        "object_type": row.object_type,
                        "object_id": row.object_id,
                        "title": row.title,
                        "description": row.description or "",
                        "tags": row.tags or [],
                        "fields": row.fields or [],
                        "project_name": row.project_name,
                        "owner": row.owner,
                        "url": self._build_tableau_url(row.url, row.object_type),
                        "text_blob": row.text_blob
                    }
                    results.append(obj)
                
                return results
                
        except Exception as e:
            logger.error(f"Search by type error: {e}")
            return []
    
    def get_all_objects(self, object_type: str = None) -> List[Dict[str, Any]]:
        """Get all objects, optionally filtered by type"""
        try:
            with self.engine.begin() as conn:
                if object_type:
                    query = text("""
                        SELECT 
                            id, site_id, object_type, object_id, title, description,
                            tags, fields, project_name, owner, url, text_blob
                        FROM chatbot.objects 
                        WHERE object_type = :object_type
                        ORDER BY title
                    """)
                    result = conn.execute(query, {"object_type": object_type})
                else:
                    query = text("""
                        SELECT 
                            id, site_id, object_type, object_id, title, description,
                            tags, fields, project_name, owner, url, text_blob
                        FROM chatbot.objects 
                        ORDER BY object_type, title
                    """)
                    result = conn.execute(query)
                
                results = []
                for row in result:
                    obj = {
                        "id": row.id,
                        "site_id": row.site_id,
                        "object_type": row.object_type,
                        "object_id": row.object_id,
                        "title": row.title,
                        "description": row.description or "",
                        "tags": row.tags or [],
                        "fields": row.fields or [],
                        "project_name": row.project_name,
                        "owner": row.owner,
                        "url": self._build_tableau_url(row.url, row.object_type),
                        "text_blob": row.text_blob
                    }
                    results.append(obj)
                
                return results
                
        except Exception as e:
            logger.error(f"Get all objects error: {e}")
            return []
