"""
Tableau Metadata GraphQL Client for RWA Chatbot Phase 1
Fetches comprehensive metadata about Tableau objects using GraphQL API
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# GraphQL endpoint for metadata
METADATA_ENDPOINT = "/api/metadata/graphql"

# Comprehensive metadata query
METADATA_QUERY = """
query Objects($siteId: ID!) {
  site(id: $siteId) {
    workbooks { 
      id
      name 
      description
      projectName 
      owner { 
        name 
        email
      }
      tags { 
        name 
      }
      createdAt
      updatedAt
      contentUrl
    }
    publishedDatasources { 
      id
      name 
      description
      projectName 
      owner { 
        name 
        email
      }
      fields { 
        name 
        description
        dataType
        isNullable
      } 
      tags { 
        name 
      }
      createdAt
      updatedAt
      contentUrl
    }
    views {
      id 
      name 
      description
      sheetType 
      workbook { 
        id
        name 
        projectName 
      }
      tags { 
        name 
      }
      datasourceFields: dataSources { 
        id
        name
        fields { 
          name 
          description
          dataType
        } 
      }
      owner { 
        name 
        email
      }
      contentUrl
      createdAt
      updatedAt
    }
  }
}
"""

# Separate queries for better performance
WORKBOOKS_QUERY = """
query Workbooks($siteId: ID!) {
  site(id: $siteId) {
    workbooks { 
      id
      name 
      description
      projectName 
      owner { 
        name 
        email
      }
      tags { 
        name 
      }
      createdAt
      updatedAt
      contentUrl
    }
  }
}
"""

DATASOURCES_QUERY = """
query Datasources($siteId: ID!) {
  site(id: $siteId) {
    publishedDatasources { 
      id
      name 
      description
      projectName 
      owner { 
        name 
        email
      }
      fields { 
        name 
        description
        dataType
        isNullable
      } 
      tags { 
        name 
      }
      createdAt
      updatedAt
      contentUrl
    }
  }
}
"""

VIEWS_QUERY = """
query Views($siteId: ID!) {
  site(id: $siteId) {
    views {
      id 
      name 
      description
      sheetType 
      workbook { 
        id
        name 
        projectName 
      }
      tags { 
        name 
      }
      datasourceFields: dataSources { 
        id
        name
        fields { 
          name 
          description
          dataType
        } 
      }
      owner { 
        name 
        email
      }
      contentUrl
      createdAt
      updatedAt
    }
  }
}
"""


class MetadataClient:
    """GraphQL client for fetching Tableau metadata"""
    
    def __init__(self, server: str, token: str):
        self.server = server.rstrip('/')
        self.token = token
        self.session = requests.Session()
    
    def _headers(self) -> Dict[str, str]:
        """Get authentication headers for GraphQL requests"""
        return {
            "X-Tableau-Auth": self.token,
            "Content-Type": "application/json"
        }
    
    def _execute_query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a GraphQL query
        
        Args:
            query: GraphQL query string
            variables: Query variables
            
        Returns:
            GraphQL response data
        """
        url = f"{self.server}{METADATA_ENDPOINT}"
        payload = {
            "query": query,
            "variables": variables
        }
        
        try:
            response = self.session.post(
                url,
                headers=self._headers(),
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                logger.error(f"GraphQL errors: {result['errors']}")
                raise Exception(f"GraphQL errors: {result['errors']}")
            
            return result["data"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GraphQL request failed: {e}")
            raise
        except KeyError as e:
            logger.error(f"Unexpected GraphQL response format: {e}")
            raise
    
    def fetch_all_metadata(self, site_id: str) -> Dict[str, Any]:
        """
        Fetch all metadata for a site using the comprehensive query
        
        Args:
            site_id: Tableau site ID
            
        Returns:
            Dictionary containing all site metadata
        """
        logger.info(f"Fetching all metadata for site {site_id}")
        
        try:
            data = self._execute_query(METADATA_QUERY, {"siteId": site_id})
            site_data = data["site"]
            
            # Log summary
            workbooks_count = len(site_data.get("workbooks", []))
            datasources_count = len(site_data.get("publishedDatasources", []))
            views_count = len(site_data.get("views", []))
            
            logger.info(f"Retrieved metadata: {workbooks_count} workbooks, {datasources_count} datasources, {views_count} views")
            
            return site_data
            
        except Exception as e:
            logger.error(f"Failed to fetch all metadata: {e}")
            raise
    
    def fetch_workbooks(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Fetch workbook metadata only
        
        Args:
            site_id: Tableau site ID
            
        Returns:
            List of workbook metadata dictionaries
        """
        logger.info(f"Fetching workbook metadata for site {site_id}")
        
        try:
            data = self._execute_query(WORKBOOKS_QUERY, {"siteId": site_id})
            workbooks = data["site"]["workbooks"]
            
            logger.info(f"Retrieved {len(workbooks)} workbooks")
            return workbooks
            
        except Exception as e:
            logger.error(f"Failed to fetch workbooks: {e}")
            raise
    
    def fetch_datasources(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Fetch datasource metadata only
        
        Args:
            site_id: Tableau site ID
            
        Returns:
            List of datasource metadata dictionaries
        """
        logger.info(f"Fetching datasource metadata for site {site_id}")
        
        try:
            data = self._execute_query(DATASOURCES_QUERY, {"siteId": site_id})
            datasources = data["site"]["publishedDatasources"]
            
            logger.info(f"Retrieved {len(datasources)} datasources")
            return datasources
            
        except Exception as e:
            logger.error(f"Failed to fetch datasources: {e}")
            raise
    
    def fetch_views(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Fetch view metadata only
        
        Args:
            site_id: Tableau site ID
            
        Returns:
            List of view metadata dictionaries
        """
        logger.info(f"Fetching view metadata for site {site_id}")
        
        try:
            data = self._execute_query(VIEWS_QUERY, {"siteId": site_id})
            views = data["site"]["views"]
            
            logger.info(f"Retrieved {len(views)} views")
            return views
            
        except Exception as e:
            logger.error(f"Failed to fetch views: {e}")
            raise
    
    def fetch_metadata_by_type(self, site_id: str, object_types: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch metadata for specific object types
        
        Args:
            site_id: Tableau site ID
            object_types: List of object types to fetch ('workbooks', 'datasources', 'views')
            
        Returns:
            Dictionary with object type as key and metadata list as value
        """
        result = {}
        
        if "workbooks" in object_types:
            result["workbooks"] = self.fetch_workbooks(site_id)
        
        if "datasources" in object_types:
            result["datasources"] = self.fetch_datasources(site_id)
        
        if "views" in object_types:
            result["views"] = self.fetch_views(site_id)
        
        return result


def normalize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize metadata from GraphQL response to a consistent format
    
    Args:
        metadata: Raw metadata from GraphQL response
        
    Returns:
        Normalized metadata dictionary
    """
    normalized = {
        "workbooks": [],
        "datasources": [],
        "views": []
    }
    
    # Normalize workbooks
    for wb in metadata.get("workbooks", []):
        normalized["workbooks"].append({
            "id": wb.get("id"),
            "name": wb.get("name"),
            "description": wb.get("description"),
            "project_name": wb.get("projectName"),
            "owner": wb.get("owner", {}).get("name"),
            "owner_email": wb.get("owner", {}).get("email"),
            "tags": [tag.get("name") for tag in wb.get("tags", [])],
            "created_at": wb.get("createdAt"),
            "updated_at": wb.get("updatedAt"),
            "url": wb.get("contentUrl"),
            "object_type": "workbook"
        })
    
    # Normalize datasources
    for ds in metadata.get("publishedDatasources", []):
        normalized["datasources"].append({
            "id": ds.get("id"),
            "name": ds.get("name"),
            "description": ds.get("description"),
            "project_name": ds.get("projectName"),
            "owner": ds.get("owner", {}).get("name"),
            "owner_email": ds.get("owner", {}).get("email"),
            "fields": [field.get("name") for field in ds.get("fields", [])],
            "field_details": [
                {
                    "name": field.get("name"),
                    "description": field.get("description"),
                    "data_type": field.get("dataType"),
                    "is_nullable": field.get("isNullable")
                }
                for field in ds.get("fields", [])
            ],
            "tags": [tag.get("name") for tag in ds.get("tags", [])],
            "created_at": ds.get("createdAt"),
            "updated_at": ds.get("updatedAt"),
            "url": ds.get("contentUrl"),
            "object_type": "datasource"
        })
    
    # Normalize views
    for view in metadata.get("views", []):
        normalized["views"].append({
            "id": view.get("id"),
            "name": view.get("name"),
            "description": view.get("description"),
            "sheet_type": view.get("sheetType"),
            "workbook": {
                "id": view.get("workbook", {}).get("id"),
                "name": view.get("workbook", {}).get("name"),
                "project_name": view.get("workbook", {}).get("projectName")
            },
            "owner": view.get("owner", {}).get("name"),
            "owner_email": view.get("owner", {}).get("email"),
            "tags": [tag.get("name") for tag in view.get("tags", [])],
            "datasources": [
                {
                    "id": ds.get("id"),
                    "name": ds.get("name"),
                    "fields": [field.get("name") for field in ds.get("fields", [])]
                }
                for ds in view.get("datasourceFields", [])
            ],
            "created_at": view.get("createdAt"),
            "updated_at": view.get("updatedAt"),
            "url": view.get("contentUrl"),
            "object_type": "view"
        })
    
    return normalized
