"""
LangChain tools for Tableau data querying
Provides tools for querying actual data from Tableau datasources
"""

import logging
from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from src.tableau.enhanced_client import EnhancedTableauClient
from src.search.semantic_search import SemanticSearch

logger = logging.getLogger(__name__)


class TableauDataQueryInput(BaseModel):
    """Input for Tableau data query tool"""
    query: str = Field(..., description="Natural language query about the data")
    datasource_id: Optional[str] = Field(None, description="Specific datasource ID to query")
    limit: int = Field(100, description="Maximum number of rows to return")


class TableauDataQueryTool(BaseTool):
    """Tool for querying Tableau datasources"""
    
    name = "query_tableau_data"
    description = "Query actual data from Tableau datasources. Use this when users ask about specific data values, trends, or insights."
    args_schema = TableauDataQueryInput
    
    def __init__(self, tableau_client: EnhancedTableauClient):
        super().__init__()
        self.tableau_client = tableau_client
    
    def _run(self, query: str, datasource_id: Optional[str] = None, limit: int = 100) -> str:
        """Execute data query"""
        try:
            # For now, return a placeholder response
            # In a full implementation, this would connect to Tableau's VizQL Data Service
            return f"Data query placeholder: '{query}' against datasource '{datasource_id}' (limit: {limit})"
        except Exception as e:
            logger.error(f"Data query error: {e}")
            return f"Error querying data: {str(e)}"


class TableauObjectSearchInput(BaseModel):
    """Input for Tableau object search tool"""
    query: str = Field(..., description="Search query for Tableau objects")
    object_type: Optional[str] = Field(None, description="Filter by object type (workbook, view, datasource)")
    limit: int = Field(10, description="Maximum number of results")


class TableauObjectSearchTool(BaseTool):
    """Tool for searching Tableau objects"""
    
    name = "search_tableau_objects"
    description = "Search for Tableau workbooks, views, and datasources. Use this when users ask 'where can I find' or 'show me' questions."
    args_schema = TableauObjectSearchInput
    
    def __init__(self, search_engine: SemanticSearch):
        super().__init__()
        self.search_engine = search_engine
    
    def _run(self, query: str, object_type: Optional[str] = None, limit: int = 10) -> str:
        """Execute object search"""
        try:
            if object_type:
                results = self.search_engine.search_by_type(query, object_type, limit)
            else:
                results = self.search_engine.search(query, limit)
            
            if not results:
                return f"No Tableau objects found matching '{query}'"
            
            response = f"Found {len(results)} Tableau object(s):\n\n"
            for i, result in enumerate(results, 1):
                obj_type = result.get("object_type", "object").title()
                title = result.get("title", "Untitled")
                description = result.get("description", "")
                project = result.get("project_name", "")
                deep_link = result.get("deep_link_url", "")
                similarity = result.get("similarity_score", 0.0)
                
                response += f"{i}. **{title}** ({obj_type})\n"
                if description:
                    response += f"   Description: {description}\n"
                if project:
                    response += f"   Project: {project}\n"
                if deep_link:
                    response += f"   Link: {deep_link}\n"
                response += f"   Relevance: {similarity:.1%}\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Object search error: {e}")
            return f"Error searching objects: {str(e)}"


class TableauDatasourceInfoInput(BaseModel):
    """Input for datasource info tool"""
    datasource_id: str = Field(..., description="Datasource ID to get information about")


class TableauDatasourceInfoTool(BaseTool):
    """Tool for getting datasource information"""
    
    name = "get_datasource_info"
    description = "Get detailed information about a specific Tableau datasource including fields and schema."
    args_schema = TableauDatasourceInfoInput
    
    def __init__(self, search_engine: SemanticSearch):
        super().__init__()
        self.search_engine = search_engine
    
    def _run(self, datasource_id: str) -> str:
        """Get datasource information"""
        try:
            # Search for the datasource
            results = self.search_engine.search(datasource_id, limit=1)
            
            if not results:
                return f"Datasource '{datasource_id}' not found"
            
            result = results[0]
            if result.get("object_type") != "datasource":
                return f"Object '{datasource_id}' is not a datasource"
            
            response = f"**Datasource: {result.get('title', 'Untitled')}**\n\n"
            
            if result.get("description"):
                response += f"Description: {result.get('description')}\n\n"
            
            if result.get("project_name"):
                response += f"Project: {result.get('project_name')}\n\n"
            
            if result.get("owner"):
                response += f"Owner: {result.get('owner')}\n\n"
            
            fields = result.get("fields", [])
            if fields:
                response += f"Fields ({len(fields)}):\n"
                for field in fields[:10]:  # Show first 10 fields
                    response += f"- {field}\n"
                if len(fields) > 10:
                    response += f"... and {len(fields) - 10} more fields\n"
            
            if result.get("tags"):
                response += f"\nTags: {', '.join(result.get('tags', []))}\n"
            
            if result.get("deep_link_url"):
                response += f"\nLink: {result.get('deep_link_url')}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Datasource info error: {e}")
            return f"Error getting datasource info: {str(e)}"


class TableauSimilarObjectsInput(BaseModel):
    """Input for similar objects tool"""
    object_id: str = Field(..., description="Object ID to find similar objects for")
    limit: int = Field(5, description="Maximum number of similar objects")


class TableauSimilarObjectsTool(BaseTool):
    """Tool for finding similar objects"""
    
    name = "find_similar_objects"
    description = "Find Tableau objects similar to a given object. Use this when users ask for 'similar' or 'related' objects."
    args_schema = TableauSimilarObjectsInput
    
    def __init__(self, search_engine: SemanticSearch):
        super().__init__()
        self.search_engine = search_engine
    
    def _run(self, object_id: str, limit: int = 5) -> str:
        """Find similar objects"""
        try:
            similar_objects = self.search_engine.get_similar_objects(object_id, limit)
            
            if not similar_objects:
                return f"No similar objects found for '{object_id}'"
            
            response = f"Found {len(similar_objects)} similar object(s):\n\n"
            for i, obj in enumerate(similar_objects, 1):
                obj_type = obj.get("object_type", "object").title()
                title = obj.get("title", "Untitled")
                description = obj.get("description", "")
                similarity = obj.get("similarity_score", 0.0)
                
                response += f"{i}. **{title}** ({obj_type})\n"
                if description:
                    response += f"   Description: {description}\n"
                response += f"   Similarity: {similarity:.1%}\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Similar objects error: {e}")
            return f"Error finding similar objects: {str(e)}"


def create_tableau_tools(tableau_client: EnhancedTableauClient, search_engine: SemanticSearch) -> List[BaseTool]:
    """Create all Tableau tools for LangChain"""
    return [
        TableauObjectSearchTool(search_engine),
        TableauDataQueryTool(tableau_client),
        TableauDatasourceInfoTool(search_engine),
        TableauSimilarObjectsTool(search_engine)
    ]
