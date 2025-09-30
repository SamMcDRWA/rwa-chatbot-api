"""
RWA Adele AI Agent - Intelligent reasoning and tool usage
"""
import os
import json
import psycopg2
from typing import List, Dict, Any, Optional
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

class RWAAgent:
    """Intelligent AI agent for RWA pharmacy chatbot"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv('OPENAI_API_KEY')
        )
        self.memory = ConversationBufferWindowMemory(
            k=10,
            memory_key="chat_history",
            return_messages=True
        )
        self.tools = self._create_tools()
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(os.getenv('DATABASE_URL'))
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent to use"""
        return [
            Tool(
                name="search_modules",
                description="Search for pharmacy modules by keywords, module numbers, or descriptions. Use this for general searches.",
                func=self._search_modules
            ),
            Tool(
                name="get_module_details",
                description="Get detailed information about a specific module by its exact title or module number (e.g., '13.20', '2.30'). Use this when user asks for details about a specific module.",
                func=self._get_module_details
            ),
            Tool(
                name="search_by_category",
                description="Search for modules by category (financial, patient care, inventory, compliance, etc.). Use this when user mentions broad categories.",
                func=self._search_by_category
            ),
            Tool(
                name="find_similar_modules",
                description="Find modules similar to a given module. Use this when user asks for 'similar' or 'related' modules.",
                func=self._find_similar_modules
            ),
            Tool(
                name="list_all_modules",
                description="List all available modules in a specific project or category. Use this when user asks to 'show all' or 'list' modules.",
                func=self._list_all_modules
            )
        ]
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the query to determine the best approach"""
        query_lower = query.lower().strip()
        
        # Check for greetings and casual conversation
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "how are you", "how's it going"]
        is_greeting = any(greeting in query_lower for greeting in greetings) or query_lower in ["hi", "hello", "hey"]
        
        # Check for help requests
        help_phrases = ["help", "what can you do", "what do you do", "how do you work", "assist"]
        is_help_request = any(phrase in query_lower for phrase in help_phrases)
        
        # Check for specific module numbers (e.g., "13.20", "2.30")
        import re
        module_numbers = re.findall(r'(\d+\.\d+)', query)
        
        # Check for detail requests
        detail_phrases = ["details", "tell me about", "explain", "what is", "describe"]
        asking_for_details = any(phrase in query_lower for phrase in detail_phrases)
        
        # Check for category searches
        categories = {
            "financial": ["financial", "sales", "margin", "revenue", "money"],
            "patient": ["patient", "care", "service", "clinical", "nms", "mur", "health"],
            "inventory": ["stock", "inventory", "product", "dispensing", "supply"],
            "compliance": ["compliance", "regulatory", "audit", "quality"],
            "nms": ["nms", "new medicine service", "medicine service"]
        }
        
        detected_category = None
        for category, keywords in categories.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_category = category
                break
        
        return {
            "is_greeting": is_greeting,
            "is_help_request": is_help_request,
            "module_numbers": module_numbers,
            "asking_for_details": asking_for_details,
            "category": detected_category,
            "is_ambiguous": any(phrase in query_lower for phrase in ["it", "this", "that", "the module"])
        }
    
    def _search_modules(self, query: str) -> str:
        """Search for modules using semantic search"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Enhanced search query with better pattern matching
            search_query = """
            SELECT 
                object_type,
                title,
                description,
                project_name,
                url,
                text_blob,
                similarity_score
            FROM (
                SELECT 
                    object_type,
                    title,
                    description,
                    project_name,
                    url,
                    text_blob,
                    CASE 
                        WHEN title ILIKE %s THEN 1.0
                        WHEN title ILIKE %s THEN 0.9
                        WHEN title ILIKE %s THEN 0.8
                        WHEN text_blob ILIKE %s THEN 0.7
                        WHEN description ILIKE %s THEN 0.6
                        ELSE 0.5
                    END as similarity_score
                FROM chatbot.objects 
                WHERE object_type = 'workbook'
            ) ranked
            WHERE similarity_score > 0.5
            ORDER BY similarity_score DESC, title
            LIMIT 10
            """
            
            query_lower = query.lower()
            
            # Create multiple search patterns for better matching
            patterns = [
                f"%{query_lower}%",  # Contains in title
                f"{query_lower}%",   # Starts with query
                f"% {query_lower} %", # Word boundary match
                f"%{query_lower}%",  # Contains in text_blob
                f"%{query_lower}%"   # Contains in description
            ]
            
            cursor.execute(search_query, patterns)
            results = cursor.fetchall()
            
            if not results:
                # Try a broader search with the first word only
                words = query_lower.split()
                if words:
                    first_word = words[0]
                    word_patterns = [
                        f"%{first_word}%",
                        f"{first_word}%",
                        f"% {first_word} %",
                        f"%{first_word}%",
                        f"%{first_word}%"
                    ]
                    
                    cursor.execute(search_query, word_patterns)
                    results = cursor.fetchall()
            
            if not results:
                return f"No modules found matching '{query}'"
            
            response = f"Found {len(results)} module(s) matching '{query}':\n\n"
            for i, (obj_type, title, desc, project, url, text_blob, score) in enumerate(results, 1):
                response += f"{i}. **{title}** ({project})\n"
                if desc and len(desc) > 50:
                    # Try to parse JSON description
                    try:
                        desc_data = json.loads(desc)
                        if isinstance(desc_data, dict) and desc_data.get('detailed_description'):
                            # Clean the markdown formatting
                            cleaned_desc = self._clean_markdown_formatting(desc_data['detailed_description'])
                            response += f"   {cleaned_desc[:100]}...\n"
                    except:
                        # Clean the description if it's a string
                        cleaned_desc = self._clean_markdown_formatting(desc)
                        response += f"   {cleaned_desc[:100]}...\n"
                response += f"   Relevance: {score:.1%}\n\n"
            
            cursor.close()
            conn.close()
            return response
            
        except Exception as e:
            return f"Error searching modules: {str(e)}"
    
    def _clean_markdown_formatting(self, text: str) -> str:
        """Clean markdown formatting to use proper formatting"""
        if not text:
            return text
        
        # Replace ### headers with **bold** formatting
        text = text.replace('### Purpose', '**Purpose:**')
        text = text.replace('### Key Metrics', '**Key Metrics:**')
        text = text.replace('### How to Use', '**How to Use:**')
        text = text.replace('### Target Audience', '**Target Audience:**')
        text = text.replace('### Usage Notes', '**Usage Notes:**')
        text = text.replace('### Features', '**Features:**')
        text = text.replace('### Benefits', '**Benefits:**')
        
        # Replace any remaining ### with **
        import re
        text = re.sub(r'###\s*([^#\n]+)', r'**\1:**', text)
        
        return text

    def _get_module_details(self, module_identifier: str) -> str:
        """Get detailed information about a specific module"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Search for module by number or title
            search_query = """
            SELECT 
                object_type,
                title,
                description,
                project_name,
                url,
                text_blob
            FROM chatbot.objects 
            WHERE object_type = 'workbook' 
            AND (title ILIKE %s OR title ILIKE %s)
            ORDER BY 
                CASE WHEN title ILIKE %s THEN 1 ELSE 2 END,
                title
            LIMIT 1
            """
            
            patterns = [
                f"%{module_identifier}%",
                f"{module_identifier}%",
                f"{module_identifier}%"
            ]
            
            cursor.execute(search_query, patterns)
            result = cursor.fetchone()
            
            if not result:
                return f"Module '{module_identifier}' not found. Try searching for it first."
            
            obj_type, title, description, project_name, url, text_blob = result
            
            response = f"**{title}**\n"
            response += f"*({project_name})*\n\n"
            
            # Try to parse rich description
            if description:
                try:
                    desc_data = json.loads(description)
                    if isinstance(desc_data, dict):
                        if desc_data.get('detailed_description'):
                            # Clean the markdown formatting
                            cleaned_desc = self._clean_markdown_formatting(desc_data['detailed_description'])
                            response += f"{cleaned_desc}\n\n"
                        
                        if desc_data.get('purpose'):
                            response += f"**Purpose:**\n{desc_data['purpose']}\n\n"
                        
                        if desc_data.get('key_metrics'):
                            metrics = desc_data['key_metrics']
                            if isinstance(metrics, list):
                                response += "**Key Metrics:**\n"
                                for metric in metrics:
                                    response += f"• {metric}\n"
                                response += "\n"
                        
                        if desc_data.get('usage_notes'):
                            response += f"**How to Use:**\n{desc_data['usage_notes']}\n\n"
                        
                        if desc_data.get('target_audience'):
                            response += f"**Target Audience:**\n{desc_data['target_audience']}\n\n"
                    else:
                        # Clean the description if it's a string
                        cleaned_desc = self._clean_markdown_formatting(description)
                        response += f"{cleaned_desc}\n\n"
                except:
                    response += f"{description}\n\n"
            else:
                # Generate intelligent fallback based on title
                title_lower = title.lower()
                if any(word in title_lower for word in ["financial", "sales", "margin"]):
                    response += "This module focuses on financial performance and reporting. It tracks financial metrics, sales data, margins, and revenue analysis to help optimize pharmacy operations.\n\n"
                elif any(word in title_lower for word in ["patient", "care", "service", "clinical", "nms", "mur"]):
                    response += "This module focuses on patient care and clinical services. It monitors patient care delivery, clinical services, and health outcomes to ensure quality care.\n\n"
                elif any(word in title_lower for word in ["stock", "inventory", "product"]):
                    response += "This module focuses on inventory and product management. It manages stock levels, product performance, and dispensing operations.\n\n"
                else:
                    response += "This module provides insights into pharmacy operations and performance to help optimize decision-making.\n\n"
            
            cursor.close()
            conn.close()
            return response
            
        except Exception as e:
            return f"Error getting module details: {str(e)}"
    
    def _search_by_category(self, category: str) -> str:
        """Search modules by category"""
        category_keywords = {
            "financial": ["financial", "sales", "margin", "revenue", "cost", "money"],
            "patient": ["patient", "care", "service", "clinical", "nms", "mur", "health"],
            "inventory": ["stock", "inventory", "product", "dispensing", "supply"],
            "compliance": ["compliance", "regulatory", "audit", "quality", "standard"],
            "staff": ["staff", "productivity", "performance", "management", "employee"]
        }
        
        keywords = category_keywords.get(category.lower(), [category])
        query = " OR ".join(keywords)
        return self._search_modules(query)
    
    def _find_similar_modules(self, module_title: str) -> str:
        """Find modules similar to the given one"""
        return self._search_modules(module_title)
    
    def _list_all_modules(self, project: str = None) -> str:
        """List all modules, optionally filtered by project"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            if project:
                query = """
                SELECT title, project_name, description
                FROM chatbot.objects 
                WHERE object_type = 'workbook' AND project_name ILIKE %s
                ORDER BY project_name, title
                """
                cursor.execute(query, [f"%{project}%"])
            else:
                query = """
                SELECT title, project_name, description
                FROM chatbot.objects 
                WHERE object_type = 'workbook'
                ORDER BY project_name, title
                """
                cursor.execute(query)
            
            results = cursor.fetchall()
            
            if not results:
                return f"No modules found for project '{project}'" if project else "No modules found"
            
            response = f"Found {len(results)} module(s):\n\n"
            current_project = None
            
            for title, proj_name, desc in results:
                if proj_name != current_project:
                    response += f"**{proj_name}**\n"
                    current_project = proj_name
                
                response += f"• {title}\n"
                if desc and len(desc) > 50:
                    try:
                        desc_data = json.loads(desc)
                        if isinstance(desc_data, dict) and desc_data.get('detailed_description'):
                            # Clean the markdown formatting
                            cleaned_desc = self._clean_markdown_formatting(desc_data['detailed_description'])
                            response += f"  {cleaned_desc[:80]}...\n"
                    except:
                        # Clean the description if it's a string
                        cleaned_desc = self._clean_markdown_formatting(desc)
                        response += f"  {cleaned_desc[:80]}...\n"
                response += "\n"
            
            cursor.close()
            conn.close()
            return response
            
        except Exception as e:
            return f"Error listing modules: {str(e)}"
    
    def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Main chat interface using ChatGPT with tool access and database grounding"""
        try:
            # Build context for ChatGPT
            system_prompt = """You are RWA Adele, an intelligent assistant for RWA Pharmacy that helps users find and understand pharmacy reports and modules.

You have access to a database of pharmacy modules and can:
- Search for modules by keywords, numbers, or categories
- Get detailed information about specific modules
- Find modules by category (financial, patient care, inventory, etc.)

IMPORTANT CONTEXT AWARENESS:
- When users ask "what does this module do?" or "tell me more about it", they are referring to the most recently mentioned module in the conversation
- When users ask "yeah what does this module do?" after you mentioned a specific module, they want details about that module
- Always maintain context from previous messages in the conversation
- If you mentioned a module number (like "13.20") in your previous response, and the user asks follow-up questions, assume they're asking about that module

When users ask about specific modules (like "13.20" or "NMS"), search the database and provide detailed information.
When users ask general questions or greetings, respond naturally and helpfully.
When users ask for "details" about something, search for it and provide comprehensive information.

Be conversational, helpful, and focus on pharmacy-related topics. Use the database information to provide accurate, contextual responses."""

            # Prepare conversation history for ChatGPT
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history to maintain context
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages
                    if msg.get("role") == "user":
                        messages.append({"role": "user", "content": msg["content"]})
                    elif msg.get("role") == "assistant":
                        messages.append({"role": "assistant", "content": msg["content"]})
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Check if this is a query that needs database search
            needs_search = self._should_search_database(message)
            
            if needs_search:
                # Get search results first
                search_results = self._get_search_results(message, conversation_history)
                
                # Add search results to context with strict grounding instruction
                if search_results and "Error" not in search_results:
                    messages.append({
                        "role": "system", 
                        "content": f"IMPORTANT: Use ONLY the information provided below from the database. Do not make up or hallucinate information. Here are the relevant modules from the database:\n\n{search_results}\n\nAnswer the user's question using ONLY this information. If the information doesn't contain what they're asking for, say so clearly. Be conversational and helpful while staying grounded in the provided data."
                    })
                else:
                    # No database results - let ChatGPT handle gracefully
                    messages.append({
                        "role": "system", 
                        "content": "No relevant information was found in the database for this query. Respond helpfully and suggest the user browse the sidebar or try different keywords."
                    })
            
            # Get response from ChatGPT
            response = self.llm.invoke(messages)
            
            # Update conversation history with new messages
            updated_history = (conversation_history or []).copy()
            updated_history.append({"role": "user", "content": message})
            updated_history.append({"role": "assistant", "content": response.content})
            
            return {
                "response": response.content,
                "conversation_history": updated_history,
                "agent_used": True
            }
            
        except Exception as e:
            return {
                "response": f"I encountered an error: {str(e)}. Please try rephrasing your question.",
                "conversation_history": conversation_history or [],
                "agent_used": False
            }
    
    def _should_search_database(self, message: str) -> bool:
        """Determine if the message needs database search"""
        message_lower = message.lower()
        
        # Don't search for simple greetings
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "how are you"]
        if any(greeting in message_lower for greeting in greetings):
            return False
        
        # Don't search for general help requests
        help_phrases = ["help", "what can you do", "what do you do", "how do you work"]
        if any(phrase in message_lower for phrase in help_phrases):
            return False
        
        # Search for anything else - including questions about modules, categories, etc.
        return True
    
    def _get_search_results(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Get search results from database"""
        try:
            # Check for specific module numbers first
            import re
            module_numbers = re.findall(r'(\d+\.\d+)', message)
            
            if module_numbers:
                # Get detailed info for specific module
                module_num = module_numbers[0]
                return self._get_module_details(module_num)
            
            # Check for context-aware queries
            if conversation_history:
                # Look for recently mentioned module numbers in conversation
                recent_modules = []
                for msg in conversation_history[-6:]:  # Last 6 messages
                    if msg.get("role") == "assistant":
                        content = msg.get("content", "")
                        # Extract module numbers from assistant responses
                        module_nums = re.findall(r'(\d+\.\d+)', content)
                        recent_modules.extend(module_nums)
                
                # If user is asking about "this module" or similar, use the most recent module
                if any(phrase in message.lower() for phrase in ["this module", "it", "that module", "what does this do", "tell me more about it", "more details", "details"]):
                    if recent_modules:
                        module_num = recent_modules[-1]  # Most recent module
                        return self._get_module_details(module_num)
            
            # Check for NMS specifically
            if "nms" in message.lower():
                return self._search_modules("nms")
            
            # Check for category searches
            analysis = self._analyze_query(message)
            if analysis["category"]:
                return self._search_by_category(analysis["category"])
            
            # General search
            return self._search_modules(message)
            
        except Exception as e:
            return f"Error searching database: {str(e)}"
    

    def _handle_ambiguous_reference(self, query: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Handle ambiguous references by analyzing conversation history"""
        if not conversation_history:
            return {
                "response": "I'd be happy to help! Could you please specify which module or report you'd like details about? You can mention the module number (like 2.30) or describe what you're looking for.",
                "conversation_history": conversation_history or [],
                "agent_used": True
            }
        
        # Look for recent module mentions
        recent_modules = []
        for msg in conversation_history[-6:]:  # Last 6 messages
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # Extract module numbers from assistant responses
                import re
                module_numbers = re.findall(r'(\d+\.\d+)', content)
                for module_num in module_numbers:
                    if module_num not in [m["number"] for m in recent_modules]:
                        # Try to extract the full title
                        title_match = re.search(rf'{re.escape(module_num)}[^\n]*?(?=\n|$|\(|\*|$)', content)
                        title = title_match.group(0).strip() if title_match else f"{module_num}"
                        recent_modules.append({"number": module_num, "title": title})
        
        if len(recent_modules) == 1:
            return {
                "response": f"Are you asking about **{recent_modules[0]['title']}**?",
                "conversation_history": conversation_history or [],
                "agent_used": True
            }
        elif len(recent_modules) > 1:
            module_list = " or ".join([f"**{m['number']}**" for m in recent_modules[:2]])
            return {
                "response": f"Are you looking for details about {module_list} as discussed previously? Or something else?",
                "conversation_history": conversation_history or [],
                "agent_used": True
            }
        else:
            return {
                "response": "I'd be happy to help! Could you please specify which module or report you'd like details about? You can mention the module number (like 2.30) or describe what you're looking for.",
                "conversation_history": conversation_history or [],
                "agent_used": True
            }
