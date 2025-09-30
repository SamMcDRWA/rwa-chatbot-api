"""
Hybrid Tableau Chatbot combining metadata discovery and data querying
Uses LangChain for intelligent tool selection and conversation management
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from src.tableau.enhanced_client import EnhancedTableauClient
from src.search.semantic_search import SemanticSearch
from src.langchain.tableau_tools import create_tableau_tools

logger = logging.getLogger(__name__)


class HybridTableauBot:
    """Hybrid chatbot combining metadata discovery and data querying"""
    
    def __init__(self, openai_api_key: str, tableau_client: EnhancedTableauClient):
        self.openai_api_key = openai_api_key
        self.tableau_client = tableau_client
        self.search_engine = SemanticSearch()
        self.llm = None
        self.agent = None
        self.tools = None
        
    def initialize(self):
        """Initialize the bot with LangChain tools"""
        try:
            # Initialize LLM
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0,
                openai_api_key=self.openai_api_key
            )
            
            # Create tools
            self.tools = create_tableau_tools(self.tableau_client, self.search_engine)
            
            # Create prompt template
            prompt = PromptTemplate.from_template("""
You are a helpful Tableau assistant that can help users find Tableau objects and query data.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")
            
            # Create agent
            self.agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            # Create agent executor
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True
            )
            
            logger.info("Hybrid bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid bot: {e}")
            return False
    
    def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Chat with the hybrid bot
        
        Args:
            message: User message
            conversation_history: Previous conversation messages
            
        Returns:
            Bot response with metadata
        """
        try:
            if not self.agent_executor:
                return {
                    "response": "Bot not initialized. Please check configuration.",
                    "error": "Bot not initialized"
                }
            
            # Prepare input for agent
            agent_input = {
                "input": message,
                "agent_scratchpad": ""
            }
            
            # Execute agent
            result = self.agent_executor.invoke(agent_input)
            
            return {
                "response": result.get("output", "No response generated"),
                "tools_used": self._extract_tools_used(result),
                "conversation_id": None,  # Could be implemented for conversation tracking
                "metadata": {
                    "model": "gpt-4o",
                    "agent_type": "react",
                    "tools_available": len(self.tools)
                }
            }
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "response": f"Sorry, I encountered an error: {str(e)}",
                "error": str(e)
            }
    
    def _extract_tools_used(self, result: Dict[str, Any]) -> List[str]:
        """Extract which tools were used in the response"""
        # This is a simplified implementation
        # In practice, you'd parse the agent's execution trace
        return ["hybrid_bot"]
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools"""
        if not self.tools:
            return []
        
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools
        ]
    
    def get_bot_capabilities(self) -> Dict[str, Any]:
        """Get bot capabilities information"""
        return {
            "metadata_discovery": True,
            "data_querying": True,
            "semantic_search": True,
            "object_similarity": True,
            "conversation_memory": False,  # Could be implemented
            "tools_available": len(self.tools) if self.tools else 0,
            "model": "gpt-4o",
            "agent_type": "react"
        }


class SimpleTableauBot:
    """Simplified Tableau bot without LangChain (fallback)"""
    
    def __init__(self, tableau_client: EnhancedTableauClient):
        self.tableau_client = tableau_client
        self.search_engine = SemanticSearch()
    
    def chat(self, message: str) -> Dict[str, Any]:
        """Simple chat without LangChain"""
        try:
            # Determine query type and respond accordingly
            query_lower = message.lower()
            
            if any(word in query_lower for word in ["where", "find", "show me", "list"]):
                # Metadata search
                results = self.search_engine.search(message, limit=10)
                
                if results:
                    response = f"I found {len(results)} Tableau object(s):\n\n"
                    for i, result in enumerate(results[:5], 1):
                        obj_type = result.get("object_type", "object").title()
                        title = result.get("title", "Untitled")
                        description = result.get("description", "")
                        deep_link = result.get("deep_link_url", "")
                        
                        response += f"{i}. **{title}** ({obj_type})\n"
                        if description:
                            response += f"   {description}\n"
                        if deep_link:
                            response += f"   [Open in Tableau]({deep_link})\n"
                        response += "\n"
                    
                    if len(results) > 5:
                        response += f"... and {len(results) - 5} more results"
                else:
                    response = "I couldn't find any Tableau objects matching your query."
            
            elif any(word in query_lower for word in ["similar", "like", "related"]):
                # Similarity search
                response = "To find similar objects, please specify which object you'd like me to find similar ones for."
            
            else:
                # General help
                response = "I can help you find Tableau objects. Try asking:\n"
                response += "- 'Where can I find sales data?'\n"
                response += "- 'Show me all dashboards'\n"
                response += "- 'Find workbooks by John Smith'"
            
            return {
                "response": response,
                "tools_used": ["simple_search"],
                "metadata": {
                    "bot_type": "simple",
                    "search_results": len(results) if 'results' in locals() else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Simple bot error: {e}")
            return {
                "response": f"Sorry, I encountered an error: {str(e)}",
                "error": str(e)
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get simple bot capabilities"""
        return {
            "metadata_discovery": True,
            "data_querying": False,
            "semantic_search": True,
            "object_similarity": False,
            "conversation_memory": False,
            "bot_type": "simple"
        }
