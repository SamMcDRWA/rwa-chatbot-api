"""
Enhanced Tableau Client for RWA Chatbot Phase 1
Combines REST API and GraphQL metadata client for comprehensive data access
"""

import logging
from typing import Dict, List, Optional, Any
from .client import TableauClient
from .metadata_client import MetadataClient, normalize_metadata
from .normalize import process_metadata_for_indexing

logger = logging.getLogger(__name__)


class EnhancedTableauClient:
    """
    Enhanced Tableau client that combines REST API and GraphQL metadata access
    Provides both detailed metadata and efficient bulk operations
    """
    
    def __init__(self, server_url: str, pat_name: str, pat_secret: str, site_name: str):
        self.rest_client = TableauClient(server_url, pat_name, pat_secret, site_name)
        self.metadata_client = None
        self.server_url = server_url
        self.pat_name = pat_name
        self.pat_secret = pat_secret
        self.site_name = site_name
    
    def signin(self) -> bool:
        """
        Authenticate with Tableau Server using both REST and GraphQL clients
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Sign in with REST client first
        if not self.rest_client.signin():
            return False
        
        # Create metadata client with the same token
        self.metadata_client = MetadataClient(
            self.server_url, 
            self.rest_client.token
        )
        
        logger.info("Successfully authenticated with both REST and GraphQL APIs")
        return True
    
    def signout(self) -> bool:
        """
        Sign out from Tableau Server
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.rest_client.signout()
    
    def get_site_id(self) -> Optional[str]:
        """Get the current site ID"""
        return self.rest_client.site_id
    
    def fetch_comprehensive_metadata(self, object_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch comprehensive metadata using REST API (GraphQL fallback)
        
        Args:
            object_types: List of object types to fetch ('workbooks', 'datasources', 'views')
                         If None, fetches all types
        
        Returns:
            Dictionary containing normalized metadata
        """
        site_id = self.get_site_id()
        if not site_id:
            raise ValueError("No site ID available")
        
        logger.info("Fetching metadata using REST API (GraphQL not available)")
        
        # Use REST API to fetch data
        metadata = {
            "workbooks": [],
            "datasources": [],
            "views": []
        }
        
        try:
            # Fetch workbooks
            if object_types is None or "workbooks" in object_types:
                logger.info("Fetching workbooks...")
                workbooks = self.rest_client.list_workbooks()
                metadata["workbooks"] = workbooks
                logger.info(f"Fetched {len(workbooks)} workbooks")
            
            # Fetch datasources
            if object_types is None or "datasources" in object_types:
                logger.info("Fetching datasources...")
                datasources = self.rest_client.list_datasources()
                metadata["datasources"] = datasources
                logger.info(f"Fetched {len(datasources)} datasources")
            
            # Fetch views (from workbooks)
            if object_types is None or "views" in object_types:
                logger.info("Fetching views from workbooks...")
                all_views = []
                for workbook in metadata["workbooks"]:
                    workbook_id = workbook.get("id")
                    if workbook_id:
                        try:
                            views = self.rest_client.list_views_for_workbook(workbook_id)
                            # Add workbook info to each view
                            for view in views:
                                view["workbook"] = {
                                    "name": workbook.get("name"),
                                    "projectName": workbook.get("project", {}).get("name") if workbook.get("project") else None
                                }
                            all_views.extend(views)
                        except Exception as e:
                            logger.warning(f"Failed to fetch views for workbook {workbook_id}: {e}")
                
                metadata["views"] = all_views
                logger.info(f"Fetched {len(all_views)} views")
        
        except Exception as e:
            logger.error(f"Error fetching metadata via REST API: {e}")
            raise
        
        logger.info(f"Fetched comprehensive metadata: {len(metadata.get('workbooks', []))} workbooks, "
                   f"{len(metadata.get('datasources', []))} datasources, "
                   f"{len(metadata.get('views', []))} views")
        
        return metadata
    
    def fetch_workbooks_metadata(self) -> List[Dict[str, Any]]:
        """Fetch workbook metadata using GraphQL"""
        if not self.metadata_client:
            raise ValueError("Not authenticated. Call signin() first.")
        
        site_id = self.get_site_id()
        if not site_id:
            raise ValueError("No site ID available")
        
        return self.metadata_client.fetch_workbooks(site_id)
    
    def fetch_datasources_metadata(self) -> List[Dict[str, Any]]:
        """Fetch datasource metadata using GraphQL"""
        if not self.metadata_client:
            raise ValueError("Not authenticated. Call signin() first.")
        
        site_id = self.get_site_id()
        if not site_id:
            raise ValueError("No site ID available")
        
        return self.metadata_client.fetch_datasources(site_id)
    
    def fetch_views_metadata(self) -> List[Dict[str, Any]]:
        """Fetch view metadata using GraphQL"""
        if not self.metadata_client:
            raise ValueError("Not authenticated. Call signin() first.")
        
        site_id = self.get_site_id()
        if not site_id:
            raise ValueError("No site ID available")
        
        return self.metadata_client.fetch_views(site_id)
    
    def get_workbook_details(self, workbook_id: str) -> Dict[str, Any]:
        """Get detailed workbook information using REST API"""
        return self.rest_client.get_workbook_details(workbook_id)
    
    def list_views_for_workbook(self, workbook_id: str) -> List[Dict[str, Any]]:
        """List views for a specific workbook using REST API"""
        return self.rest_client.list_views_for_workbook(workbook_id)
    
    def create_text_blob(self, obj: Dict[str, Any]) -> str:
        """
        Create a text blob for search indexing from object metadata
        
        Args:
            obj: Object metadata dictionary
            
        Returns:
            Concatenated text string for search
        """
        text_parts = []
        
        # Add basic information
        if obj.get("name"):
            text_parts.append(obj["name"])
        
        if obj.get("description"):
            text_parts.append(obj["description"])
        
        if obj.get("project_name"):
            text_parts.append(f"Project: {obj['project_name']}")
        
        if obj.get("owner"):
            text_parts.append(f"Owner: {obj['owner']}")
        
        # Add tags
        if obj.get("tags"):
            text_parts.append(f"Tags: {', '.join(obj['tags'])}")
        
        # Add fields (for datasources and views)
        if obj.get("fields"):
            text_parts.append(f"Fields: {', '.join(obj['fields'])}")
        
        # Add datasource information (for views)
        if obj.get("datasources"):
            for ds in obj["datasources"]:
                if ds.get("name"):
                    text_parts.append(f"Datasource: {ds['name']}")
                if ds.get("fields"):
                    text_parts.append(f"Datasource fields: {', '.join(ds['fields'])}")
        
        # Add workbook information (for views)
        if obj.get("workbook"):
            wb = obj["workbook"]
            if wb.get("name"):
                text_parts.append(f"Workbook: {wb['name']}")
            if wb.get("project_name"):
                text_parts.append(f"Workbook project: {wb['project_name']}")
        
        return " ".join(text_parts)
    
    def prepare_objects_for_indexing(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Prepare objects for database indexing using REST API data
        
        Args:
            metadata: REST API metadata dictionary
            
        Returns:
            List of objects ready for database insertion
        """
        site_id = self.get_site_id()
        if not site_id:
            raise ValueError("No site ID available")
        
        objects = []
        
        # Process workbooks
        for workbook in metadata.get("workbooks", []):
            try:
                obj = {
                    "site_id": site_id,
                    "object_type": "workbook",
                    "object_id": workbook.get("id", ""),
                    "title": workbook.get("name", ""),
                    "description": workbook.get("description", ""),
                    "tags": workbook.get("tags", {}).get("tag", []) if isinstance(workbook.get("tags", {}), dict) else [],
                    "fields": [],
                    "project_name": workbook.get("project", {}).get("name") if workbook.get("project") else None,
                    "owner": workbook.get("owner", {}).get("name") if workbook.get("owner") else None,
                    "url": workbook.get("contentUrl", ""),
                    "text_blob": self._create_text_blob(
                        workbook.get("name", ""),
                        workbook.get("description", ""),
                        workbook.get("tags", {}).get("tag", []) if isinstance(workbook.get("tags", {}), dict) else [],
                        [],
                        workbook.get("project", {}).get("name") if workbook.get("project") else None,
                        workbook.get("owner", {}).get("name") if workbook.get("owner") else None
                    ),
                    "search_priority": 2  # Workbooks have medium priority
                }
                objects.append(obj)
            except Exception as e:
                logger.warning(f"Failed to process workbook {workbook.get('id', 'unknown')}: {e}")
        
        # Process datasources
        for datasource in metadata.get("datasources", []):
            try:
                obj = {
                    "site_id": site_id,
                    "object_type": "datasource",
                    "object_id": datasource.get("id", ""),
                    "title": datasource.get("name", ""),
                    "description": datasource.get("description", ""),
                    "tags": datasource.get("tags", {}).get("tag", []) if isinstance(datasource.get("tags", {}), dict) else [],
                    "fields": [],  # Would need additional API call to get fields
                    "project_name": datasource.get("project", {}).get("name") if datasource.get("project") else None,
                    "owner": datasource.get("owner", {}).get("name") if datasource.get("owner") else None,
                    "url": datasource.get("contentUrl", ""),
                    "text_blob": self._create_text_blob(
                        datasource.get("name", ""),
                        datasource.get("description", ""),
                        datasource.get("tags", {}).get("tag", []) if isinstance(datasource.get("tags", {}), dict) else [],
                        [],
                        datasource.get("project", {}).get("name") if datasource.get("project") else None,
                        datasource.get("owner", {}).get("name") if datasource.get("owner") else None
                    ),
                    "search_priority": 1  # Datasources have low priority
                }
                objects.append(obj)
            except Exception as e:
                logger.warning(f"Failed to process datasource {datasource.get('id', 'unknown')}: {e}")
        
        # Process views
        for view in metadata.get("views", []):
            try:
                obj = {
                    "site_id": site_id,
                    "object_type": "view",
                    "object_id": view.get("id", ""),
                    "title": view.get("name", ""),
                    "description": view.get("description", ""),
                    "tags": view.get("tags", {}).get("tag", []) if isinstance(view.get("tags", {}), dict) else [],
                    "fields": [],  # Would need additional API call to get fields
                    "project_name": view.get("workbook", {}).get("projectName") if view.get("workbook") else None,
                    "owner": view.get("owner", {}).get("name") if view.get("owner") else None,
                    "url": view.get("contentUrl", ""),
                    "text_blob": self._create_text_blob(
                        view.get("name", ""),
                        view.get("description", ""),
                        view.get("tags", {}).get("tag", []) if isinstance(view.get("tags", {}), dict) else [],
                        [],
                        view.get("workbook", {}).get("projectName") if view.get("workbook") else None,
                        view.get("owner", {}).get("name") if view.get("owner") else None
                    ),
                    "search_priority": 3  # Views have high priority
                }
                objects.append(obj)
            except Exception as e:
                logger.warning(f"Failed to process view {view.get('id', 'unknown')}: {e}")
        
        logger.info(f"Prepared {len(objects)} objects for indexing")
        return objects
    
    def _create_text_blob(self, title: str, description: str, tags: list, fields: list, project: str, owner: str) -> str:
        """Create a searchable text blob from object attributes"""
        import re
        
        parts = [
            title or "",
            description or "",
            " ".join(tags or []),
            " ".join(fields or []),
            project or "",
            owner or ""
        ]
        
        text = " \n ".join([p.strip() for p in parts if p])
        text = re.sub(r"\s+", " ", text)
        return text.lower()
    
    def __enter__(self):
        """Context manager entry"""
        if not self.signin():
            raise ConnectionError("Failed to authenticate with Tableau Server")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.signout()
