"""
Search API endpoints for RWA Chatbot Phase 1
Provides REST API for searching Tableau objects
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from src.search.semantic_search import SemanticSearch

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/search", tags=["search"])

# Initialize search engine lazily
search_engine = None

def get_search_engine():
    """Get search engine instance (lazy initialization)"""
    global search_engine
    if search_engine is None:
        search_engine = SemanticSearch()
    return search_engine


# Pydantic models for request/response
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query string")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    similarity_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity score")
    object_type: Optional[str] = Field(None, description="Filter by object type (workbook, view, datasource)")
    project_name: Optional[str] = Field(None, description="Filter by project name")


class SearchResult(BaseModel):
    id: int
    site_id: str
    object_type: str
    object_id: str
    title: str
    description: Optional[str]
    tags: List[str]
    fields: List[str]
    project_name: Optional[str]
    owner: Optional[str]
    url: Optional[str]
    deep_link_url: Optional[str]
    similarity_score: float
    search_priority: int


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResult]
    search_time_ms: float
    search_type: str  # "semantic" or "text"


class SearchSuggestionsResponse(BaseModel):
    suggestions: List[str]
    partial_query: str


class SearchStatsResponse(BaseModel):
    total_objects: int
    objects_with_embeddings: int
    embedding_coverage: float
    object_types: int
    projects: int
    avg_text_length: float


@router.post("/", response_model=SearchResponse)
async def search_objects(request: SearchRequest):
    """
    Search for Tableau objects using semantic search
    
    Args:
        request: Search request with query and filters
        
    Returns:
        Search results with similarity scores
    """
    try:
        import time
        start_time = time.time()
        
        # Perform search
        if request.object_type:
            results = get_search_engine().search_by_type(
                request.query, 
                request.object_type, 
                request.limit
            )
        elif request.project_name:
            results = get_search_engine().search_by_project(
                request.query, 
                request.project_name, 
                request.limit
            )
        else:
            results = get_search_engine().search(
                request.query, 
                request.limit, 
                request.similarity_threshold
            )
        
        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Determine search type
        search_type = "semantic" if any(r.get("similarity_score", 0) > 0.5 for r in results) else "text"
        
        # Convert to response format
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                id=result["id"],
                site_id=result["site_id"],
                object_type=result["object_type"],
                object_id=result["object_id"],
                title=result["title"],
                description=result.get("description"),
                tags=result.get("tags", []),
                fields=result.get("fields", []),
                project_name=result.get("project_name"),
                owner=result.get("owner"),
                url=result.get("url"),
                deep_link_url=result.get("deep_link_url"),
                similarity_score=result.get("similarity_score", 0.0),
                search_priority=result.get("search_priority", 0)
            ))
        
        return SearchResponse(
            query=request.query,
            total_results=len(search_results),
            results=search_results,
            search_time_ms=search_time,
            search_type=search_type
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(..., description="Partial query string"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of suggestions")
):
    """
    Get search suggestions based on partial query
    
    Args:
        q: Partial query string
        limit: Maximum number of suggestions
        
    Returns:
        List of search suggestions
    """
    try:
        suggestions = get_search_engine().get_search_suggestions(q, limit)
        
        return SearchSuggestionsResponse(
            suggestions=suggestions,
            partial_query=q
        )
        
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/similar/{object_id}", response_model=List[SearchResult])
async def get_similar_objects(
    object_id: str,
    limit: int = Query(5, ge=1, le=20, description="Maximum number of similar objects")
):
    """
    Find objects similar to a given object
    
    Args:
        object_id: Tableau object ID
        limit: Maximum number of similar objects
        
    Returns:
        List of similar objects
    """
    try:
        results = get_search_engine().get_similar_objects(object_id, limit)
        
        similar_objects = []
        for result in results:
            similar_objects.append(SearchResult(
                id=result["id"],
                site_id=result["site_id"],
                object_type=result["object_type"],
                object_id=result["object_id"],
                title=result["title"],
                description=result.get("description"),
                tags=result.get("tags", []),
                fields=result.get("fields", []),
                project_name=result.get("project_name"),
                owner=result.get("owner"),
                url=result.get("url"),
                deep_link_url=result.get("deep_link_url"),
                similarity_score=result.get("similarity_score", 0.0),
                search_priority=result.get("search_priority", 0)
            ))
        
        return similar_objects
        
    except Exception as e:
        logger.error(f"Similar objects error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to find similar objects: {str(e)}")


@router.get("/stats", response_model=SearchStatsResponse)
async def get_search_stats():
    """
    Get search engine statistics
    
    Returns:
        Search engine statistics
    """
    try:
        stats = get_search_engine().get_search_stats()
        
        return SearchStatsResponse(
            total_objects=stats.get("total_objects", 0),
            objects_with_embeddings=stats.get("objects_with_embeddings", 0),
            embedding_coverage=stats.get("embedding_coverage", 0.0),
            object_types=stats.get("object_types", 0),
            projects=stats.get("projects", 0),
            avg_text_length=stats.get("avg_text_length", 0.0)
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/health")
async def search_health():
    """
    Health check for search functionality
    
    Returns:
        Search engine health status
    """
    try:
        # Test search functionality
        test_results = get_search_engine().search("test", limit=1)
        
        return {
            "status": "healthy",
            "get_search_engine()": "operational",
            "test_search": "successful",
            "results_available": len(test_results) > 0
        }
        
    except Exception as e:
        logger.error(f"Search health check failed: {e}")
        return {
            "status": "unhealthy",
            "get_search_engine()": "error",
            "error": str(e)
        }
