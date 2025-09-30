"""
Semantic search module for RWA Chatbot Phase 1
Provides vector-based semantic search capabilities
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from src.database.store import get_engine

logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


class SemanticSearch:
    """Semantic search engine using vector embeddings"""
    
    def __init__(self):
        self.model = None
        self.engine = get_engine()
    
    def _load_model(self):
        """Load the sentence transformer model"""
        if self.model is None:
            logger.info(f"Loading embedding model: {MODEL_NAME}")
            self.model = SentenceTransformer(MODEL_NAME)
            logger.info("Model loaded successfully")
        return self.model
    
    def search(self, query: str, limit: int = 10, similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Perform semantic search on indexed Tableau objects
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of search results with similarity scores
        """
        if not query.strip():
            return []
        
        try:
            # Load model
            model = self._load_model()
            
            # Generate query embedding
            query_embedding = model.encode([query], normalize_embeddings=True)[0]
            
            # Search using vector similarity
            results = self._vector_search(query_embedding, limit, similarity_threshold)
            
            # Add text-based search as fallback
            if not results:
                results = self._text_search(query, limit)
            
            logger.info(f"Found {len(results)} results for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return self._text_search(query, limit)  # Fallback to text search
    
    def _vector_search(self, query_embedding: np.ndarray, limit: int, threshold: float) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        try:
            with self.engine.begin() as conn:
                # Use pgvector cosine similarity search
                query = text("""
                    SELECT 
                        id, site_id, object_type, object_id, title, description,
                        tags, fields, project_name, owner, url, text_blob,
                        1 - (embedding <=> :query_embedding) as similarity_score
                    FROM chatbot.objects 
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> :query_embedding
                    LIMIT :limit
                """)
                
                result = conn.execute(query, {
                    "query_embedding": query_embedding.tolist(),
                    "limit": limit
                }).fetchall()
                
                # Filter by similarity threshold
                results = []
                for row in result:
                    similarity = float(row.similarity_score)
                    if similarity >= threshold:
                        result_dict = dict(row._mapping)
                        result_dict["similarity_score"] = similarity
                        results.append(result_dict)
                
                return results
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _text_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback text-based search using PostgreSQL full-text search"""
        try:
            with self.engine.begin() as conn:
                # Use PostgreSQL full-text search
                search_query = text("""
                    SELECT 
                        id, site_id, object_type, object_id, title, description,
                        tags, fields, project_name, owner, url, text_blob,
                        ts_rank(to_tsvector('english', text_blob), plainto_tsquery('english', :query)) as rank_score
                    FROM chatbot.objects 
                    WHERE to_tsvector('english', text_blob) @@ plainto_tsquery('english', :query)
                    ORDER BY rank_score DESC
                    LIMIT :limit
                """)
                
                result = conn.execute(search_query, {
                    "query": query,
                    "limit": limit
                }).fetchall()
                
                results = []
                for row in result:
                    result_dict = dict(row._mapping)
                    result_dict["similarity_score"] = float(row.rank_score)
                    results.append(result_dict)
                
                return results
                
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []
    
    def search_by_type(self, query: str, object_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for specific object types only"""
        all_results = self.search(query, limit * 2)  # Get more results to filter
        filtered_results = [r for r in all_results if r.get("object_type") == object_type]
        return filtered_results[:limit]
    
    def search_by_project(self, query: str, project_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search within a specific project"""
        all_results = self.search(query, limit * 2)
        filtered_results = [r for r in all_results if project_name.lower() in r.get("project_name", "").lower()]
        return filtered_results[:limit]
    
    def get_similar_objects(self, object_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find objects similar to a given object"""
        try:
            with self.engine.begin() as conn:
                # Get the object's embedding
                get_embedding_query = text("""
                    SELECT embedding FROM chatbot.objects 
                    WHERE object_id = :object_id AND embedding IS NOT NULL
                """)
                
                result = conn.execute(get_embedding_query, {"object_id": object_id}).fetchone()
                if not result:
                    return []
                
                embedding = result[0]
                
                # Find similar objects
                similar_query = text("""
                    SELECT 
                        id, site_id, object_type, object_id, title, description,
                        tags, fields, project_name, owner, url, deep_link_url,
                        text_blob, search_priority,
                        1 - (embedding <=> :embedding) as similarity_score
                    FROM chatbot.objects 
                    WHERE object_id != :object_id AND embedding IS NOT NULL
                    ORDER BY embedding <=> :embedding
                    LIMIT :limit
                """)
                
                similar_result = conn.execute(similar_query, {
                    "embedding": embedding,
                    "object_id": object_id,
                    "limit": limit
                }).fetchall()
                
                results = []
                for row in similar_result:
                    result_dict = dict(row._mapping)
                    result_dict["similarity_score"] = float(row.similarity_score)
                    results.append(result_dict)
                
                return results
                
        except Exception as e:
            logger.error(f"Error finding similar objects: {e}")
            return []
    
    def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query"""
        try:
            with self.engine.begin() as conn:
                # Search for titles that start with the partial query
                suggestions_query = text("""
                    SELECT DISTINCT title 
                    FROM chatbot.objects 
                    WHERE LOWER(title) LIKE LOWER(:partial_query) || '%'
                    ORDER BY search_priority DESC, title
                    LIMIT :limit
                """)
                
                result = conn.execute(suggestions_query, {
                    "partial_query": partial_query,
                    "limit": limit
                }).fetchall()
                
                return [row[0] for row in result]
                
        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return []
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search statistics"""
        try:
            with self.engine.begin() as conn:
                stats_query = text("""
                    SELECT 
                        COUNT(*) as total_objects,
                        COUNT(embedding) as objects_with_embeddings,
                        COUNT(DISTINCT object_type) as object_types,
                        COUNT(DISTINCT project_name) as projects,
                        AVG(LENGTH(text_blob)) as avg_text_length
                    FROM chatbot.objects
                """)
                
                result = conn.execute(stats_query).fetchone()
                
                if result:
                    return {
                        "total_objects": result[0],
                        "objects_with_embeddings": result[1],
                        "embedding_coverage": (result[1] / result[0] * 100) if result[0] > 0 else 0,
                        "object_types": result[2],
                        "projects": result[3],
                        "avg_text_length": float(result[4]) if result[4] else 0
                    }
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {}
