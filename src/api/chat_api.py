"""
Chat API endpoints for RWA Chatbot Phase 1
Provides conversational interface for Tableau object discovery
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime
from src.search.semantic_search import SemanticSearch

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize search engine lazily
search_engine = None

def get_search_engine():
    """Get search engine instance (lazy initialization)"""
    global search_engine
    if search_engine is None:
        search_engine = SemanticSearch()
    return search_engine


# Pydantic models
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    include_similar: bool = Field(True, description="Include similar objects in response")


class ChatResponse(BaseModel):
    message: str = Field(..., description="Assistant response")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    similar_objects: List[Dict[str, Any]] = Field(default_factory=list, description="Similar objects")
    conversation_id: str = Field(..., description="Conversation ID")
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Search metadata")


class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[ChatMessage]
    created_at: str
    updated_at: str


# In-memory conversation storage (in production, use Redis or database)
conversations: Dict[str, List[ChatMessage]] = {}


def generate_conversation_id() -> str:
    """Generate a unique conversation ID"""
    import uuid
    return str(uuid.uuid4())


def get_conversation_history(conversation_id: str) -> List[ChatMessage]:
    """Get conversation history"""
    return conversations.get(conversation_id, [])


def add_message_to_conversation(conversation_id: str, message: ChatMessage):
    """Add message to conversation history"""
    if conversation_id not in conversations:
        conversations[conversation_id] = []
    conversations[conversation_id].append(message)


def format_search_results(results: List[Dict[str, Any]]) -> str:
    """Format search results for chat response"""
    if not results:
        return "I couldn't find any Tableau objects matching your query."
    
    response_parts = [f"I found {len(results)} Tableau object(s) that match your query:\n"]
    
    for i, result in enumerate(results, 1):  # Show all results
        obj_type = result.get("object_type", "object").title()
        title = result.get("title", "Untitled")
        description = result.get("description", "")
        project = result.get("project_name", "")
        owner = result.get("owner", "")
        deep_link = result.get("deep_link_url", "")
        similarity = result.get("similarity_score", 0.0)
        
        response_parts.append(f"{i}. **{title}** ({obj_type})")
        
        if description:
            response_parts.append(f"   Description: {description}")
        
        if project:
            response_parts.append(f"   Project: {project}")
        
        if owner:
            response_parts.append(f"   Owner: {owner}")
        
        if deep_link:
            response_parts.append(f"   [Open in Tableau]({deep_link})")
        
        response_parts.append(f"   Relevance: {similarity:.1%}")
        response_parts.append("")  # Empty line between results
    
    return "\n".join(response_parts)


def generate_chat_response(user_message: str, results: List[Dict[str, Any]], 
                          similar_objects: List[Dict[str, Any]] = None) -> str:
    """Generate a conversational response based on search results"""
    
    # Analyze the query to provide contextual responses
    query_lower = user_message.lower()
    
    if any(word in query_lower for word in ["where", "find", "show me", "list"]):
        # Discovery query
        if results:
            response = format_search_results(results)
            
            # Add helpful suggestions
            if len(results) == 1:
                response += "\n\nWould you like me to find similar objects or provide more details about this one?"
            elif len(results) > 1:
                response += "\n\nYou can ask me to filter by project, object type, or get more details about a specific result."
        else:
            response = "I couldn't find any Tableau objects matching your query. Try rephrasing your question or check if the objects exist in your Tableau site."
    
    elif any(word in query_lower for word in ["what", "tell me about", "describe"]):
        # Information query
        if results:
            response = format_search_results(results)
            response += "\n\nIs there anything specific you'd like to know about these objects?"
        else:
            response = "I don't have information about that. Try asking me to find specific Tableau objects first."
    
    elif any(word in query_lower for word in ["similar", "like", "related"]):
        # Similarity query
        if similar_objects:
            response = f"I found {len(similar_objects)} similar objects:\n\n"
            for i, obj in enumerate(similar_objects[:3], 1):
                response += f"{i}. **{obj.get('title', 'Untitled')}** ({obj.get('object_type', 'object').title()})\n"
                if obj.get('description'):
                    response += f"   {obj.get('description')}\n"
                response += f"   Similarity: {obj.get('similarity_score', 0.0):.1%}\n\n"
        else:
            response = "I couldn't find similar objects. Please specify which object you'd like me to find similar ones for."
    
    else:
        # General query
        if results:
            response = format_search_results(results)
        else:
            response = "I'm here to help you find Tableau objects. Try asking me things like:\n"
            response += "- 'Where can I find sales data?'\n"
            response += "- 'Show me all dashboards'\n"
            response += "- 'Find workbooks by John Smith'\n"
            response += "- 'What views are available in the Finance project?'"
    
    return response


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the Tableau assistant
    
    Args:
        request: Chat request with message and optional conversation ID
        
    Returns:
        Chat response with search results and conversation ID
    """
    try:
        # Generate or use existing conversation ID
        conversation_id = request.conversation_id or generate_conversation_id()
        
        # Get conversation history
        history = get_conversation_history(conversation_id)
        
        # Add user message to history
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now().isoformat()
        )
        add_message_to_conversation(conversation_id, user_message)
        
        # Perform search
        search_results = get_search_engine().search(request.message, limit=10)
        
        # Get similar objects if requested
        similar_objects = []
        if request.include_similar and search_results:
            # Find similar objects for the first result
            first_result = search_results[0]
            similar_objects = get_search_engine().get_similar_objects(
                first_result.get("object_id", ""), 
                limit=3
            )
        
        # Generate response
        response_text = generate_chat_response(
            request.message, 
            search_results, 
            similar_objects
        )
        
        # Add assistant message to history
        assistant_message = ChatMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat()
        )
        add_message_to_conversation(conversation_id, assistant_message)
        
        # Prepare response
        return ChatResponse(
            message=response_text,
            results=search_results,
            similar_objects=similar_objects,
            conversation_id=conversation_id,
            search_metadata={
                "total_results": len(search_results),
                "similar_objects_count": len(similar_objects),
                "search_type": "semantic" if search_results else "text"
            }
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """
    Get conversation history
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Conversation history
    """
    try:
        messages = get_conversation_history(conversation_id)
        
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationHistory(
            conversation_id=conversation_id,
            messages=messages,
            created_at=messages[0].timestamp if messages else "",
            updated_at=messages[-1].timestamp if messages else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete conversation history
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Success message
    """
    try:
        if conversation_id in conversations:
            del conversations[conversation_id]
            return {"message": "Conversation deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


@router.get("/conversations")
async def list_conversations():
    """
    List all conversations
    
    Returns:
        List of conversation IDs
    """
    try:
        return {
            "conversations": list(conversations.keys()),
            "total_count": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"List conversations error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.get("/health")
async def chat_health():
    """
    Health check for chat functionality
    
    Returns:
        Chat service health status
    """
    try:
        # Test search functionality
        test_results = get_search_engine().search("test", limit=1)
        
        return {
            "status": "healthy",
            "chat_service": "operational",
            "get_search_engine()": "connected",
            "conversations_active": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        return {
            "status": "unhealthy",
            "chat_service": "error",
            "error": str(e)
        }
