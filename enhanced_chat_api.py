#!/usr/bin/env python3
"""
Enhanced Chat API with ChatGPT-like responses
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import random
import json
from datetime import datetime
from src.agent import RWAAgent

# Load environment variables
load_dotenv()

def generate_tableau_url(workbook_id: str, title: str) -> str:
    """Generate proper Tableau URL from workbook ID and title"""
    # Get Tableau server details from environment
    tableau_server = os.getenv('TABLEAU_SERVER', 'https://prod-useast-a.online.tableau.com')
    site_id = os.getenv('TABLEAU_SITE_ID', 'rwa')
    
    # Clean the title for URL
    clean_title = title.replace(' ', '').replace('(', '').replace(')', '').replace('&', 'and')
    
    # Generate the Tableau URL
    # Format: https://server/#/site/site-id/views/workbook/sheet?iid=1
    base_url = f"{tableau_server}/#/site/{site_id}/views/{workbook_id}"
    
    # Add the sheet name and iid parameter for proper deep linking
    tableau_url = f"{base_url}?iid=1"
    
    return tableau_url

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RWA Adele Enhanced Chat API",
    description="ChatGPT-like conversational interface for RWA pharmacy data",
    version="2.0.0"
)

# Initialize the AI agent
agent = None

def get_agent():
    """Get or initialize the AI agent"""
    global agent
    if agent is None:
        try:
            agent = RWAAgent()
            logger.info("AI Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI Agent: {e}")
            return None
    return agent

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    """Get database connection with timeout"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    return psycopg2.connect(
        database_url,
        connect_timeout=10,  # 10 second timeout
        application_name="rwa_adele_api"
    )

def search_content_semantic(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search content using improved semantic similarity with exact match priority"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query_lower = query.lower()
        
        # First, try exact matches in title (highest priority)
        # This will find "13.05" exactly, not "1.05"
        exact_match_query = """
        SELECT 
            object_type,
            title,
            description,
            project_name,
            url,
            text_blob,
            1.0 as similarity_score
        FROM chatbot.objects 
        WHERE title ILIKE %s
        ORDER BY title
        LIMIT %s
        """
        
        cursor.execute(exact_match_query, [f"%{query_lower}%", limit])
        exact_results = cursor.fetchall()
        
        if exact_results:
            # If we found exact matches, return them
            cursor.close()
            conn.close()
            return [dict(row) for row in exact_results]
        
        # Second, try to extract module numbers from natural language queries
        # Look for patterns like "13.20", "13.05", etc.
        import re
        module_pattern = r'(\d+\.\d+)'
        module_matches = re.findall(module_pattern, query_lower)
        
        if module_matches:
            for module_num in module_matches:
                # Try multiple search patterns for the module number
                search_patterns = [
                    f"%{module_num}%",  # Contains the module number
                    f"{module_num} %",  # Starts with module number
                    f"% {module_num} %", # Module number in middle
                    f"% {module_num}",  # Ends with module number
                ]
                
                for pattern in search_patterns:
                    module_query = """
                    SELECT 
                        object_type,
                        title,
                        description,
                        project_name,
                        url,
                        text_blob,
                        1.0 as similarity_score
                    FROM chatbot.objects 
                    WHERE title ILIKE %s
                    ORDER BY title
                    LIMIT %s
                    """
                    
                    cursor.execute(module_query, [pattern, limit])
                    module_results = cursor.fetchall()
                    
                    if module_results:
                        cursor.close()
                        conn.close()
                        return [dict(row) for row in module_results]
        
        # If no exact matches, try partial matches with better scoring
        # Extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'reports', 'data', 'show', 'me', 'find', 'get', 'about', 'what', 'is'}
        words = [word.strip('.,!?') for word in query_lower.split() if word.strip('.,!?') not in stop_words and len(word.strip('.,!?')) > 1]
        
        if not words:
            cursor.close()
            conn.close()
            return []
        
        # Build search with better scoring
        search_query = """
        SELECT 
            object_type,
            title,
            description,
            project_name,
            url,
            text_blob,
            CASE 
                WHEN title ILIKE %s THEN 0.9
                WHEN title ILIKE %s THEN 0.8
                WHEN description ILIKE %s THEN 0.6
                WHEN project_name ILIKE %s THEN 0.4
                WHEN text_blob ILIKE %s THEN 0.2
                ELSE 0.1
            END as similarity_score
        FROM chatbot.objects 
        WHERE (
            title ILIKE %s OR 
            description ILIKE %s OR 
            project_name ILIKE %s OR
            text_blob ILIKE %s
        )
        ORDER BY similarity_score DESC, title
        LIMIT %s
        """
        
        # Use the first meaningful word for search
        search_term = words[0]
        search_params = [
            f"%{search_term}%",  # title exact
            f"%{query_lower}%",  # title partial
            f"%{search_term}%",  # description
            f"%{search_term}%",  # project_name
            f"%{search_term}%",  # text_blob
            f"%{search_term}%",  # WHERE title
            f"%{search_term}%",  # WHERE description
            f"%{search_term}%",  # WHERE project_name
            f"%{search_term}%",  # WHERE text_blob
            limit
        ]
        
        cursor.execute(search_query, search_params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [dict(row) for row in results]
        
    except Exception as e:
        logger.error(f"Database search error: {e}")
        return []

def get_workbooks() -> List[Dict[str, Any]]:
    """Get all workbooks from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT title, project_name, url
            FROM chatbot.objects 
            WHERE object_type = 'workbook'
            ORDER BY title
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [dict(row) for row in results]
        
    except Exception as e:
        logger.error(f"Database error getting workbooks: {e}")
        return []

def get_projects() -> List[Dict[str, Any]]:
    """Get all projects with their workbooks using real Tableau project names"""
    conn = None
    cursor = None
    try:
        logger.info("Starting get_projects()")
        conn = get_db_connection()
        logger.info("Database connection established")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all workbooks grouped by real project names
        logger.info("Executing projects query")
        cursor.execute("""
            SELECT project_name, object_id, title, url, description
            FROM chatbot.objects 
            WHERE object_type = 'workbook' 
            AND project_name IS NOT NULL
            ORDER BY project_name, title
        """)
        
        results = cursor.fetchall()
        logger.info(f"Retrieved {len(results)} workbooks from database")
        
        # Group workbooks by project
        projects_dict = {}
        for row in results:
            project_name = row['project_name']
            workbook = {
                'id': row['object_id'],
                'title': row['title'],
                'url': row['url'],
                'description': row['description'] or ''
            }
            
            if project_name not in projects_dict:
                projects_dict[project_name] = {
                    'project_name': project_name,
                    'workbooks': []
                }
            
            projects_dict[project_name]['workbooks'].append(workbook)
        
        # Convert to list
        projects = list(projects_dict.values())
        
        logger.info(f"Returning {len(projects)} projects")
        return projects
        
    except Exception as e:
        logger.error(f"Database error getting projects: {e}")
        return []

def get_latest_news() -> List[Dict[str, Any]]:
    """Get latest news articles from database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get latest news articles from database
        cursor.execute("""
            SELECT id, title, summary, url, source, category, published_date
            FROM chatbot.news_articles 
            WHERE is_active = TRUE 
            ORDER BY published_date DESC 
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        if not results:
            # Return mock data if no real articles in database
            logger.info("No news articles in database, returning mock data")
            return get_mock_news()
        
        # Convert to list of dictionaries
        news_articles = []
        for row in results:
            news_articles.append({
                "id": row['id'],
                "title": row['title'],
                "summary": row['summary'] or "",
                "url": row['url'] or "",
                "source": row['source'] or "Unknown",
                "category": row['category'] or "General",
                "published_date": row['published_date'].isoformat() if row['published_date'] else None
            })
        
        logger.info(f"Returning {len(news_articles)} news articles from database")
        return news_articles
        
    except Exception as e:
        logger.error(f"Error getting news from database: {e}")
        # Fallback to mock data
        return get_mock_news()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_mock_news() -> List[Dict[str, Any]]:
    """Get mock news data as fallback"""
    return [
        {
            "id": 1,
            "title": "New Pharmacy Regulations Announced",
            "summary": "The latest updates to pharmacy regulations have been published, affecting dispensing practices across the UK.",
            "source": "PharmacyBiz",
            "url": "https://example.com/news1",
            "published_date": "2024-01-15T10:30:00Z",
            "category": "Regulations"
        },
        {
            "id": 2,
            "title": "NHS Digital Transformation Update",
            "summary": "NHS continues its digital transformation journey with new tools for community pharmacies.",
            "source": "NHS",
            "url": "https://example.com/news2",
            "published_date": "2024-01-14T14:20:00Z",
            "category": "Technology"
        },
        {
            "id": 3,
            "title": "CPE Training Requirements Changed",
            "summary": "Continuing Professional Education requirements have been updated for pharmacy professionals.",
            "source": "CPE",
            "url": "https://example.com/news3",
            "published_date": "2024-01-13T09:15:00Z",
            "category": "Education"
        },
        {
            "id": 4,
            "title": "Medication Shortage Alert",
            "summary": "Important updates on medication shortages affecting community pharmacies nationwide.",
            "source": "PharmacyBiz",
            "url": "https://example.com/news4",
            "published_date": "2024-01-12T16:45:00Z",
            "category": "Supply Chain"
        },
        {
            "id": 5,
            "title": "New Prescription Guidelines",
            "summary": "Updated guidelines for prescription handling and patient safety measures.",
            "source": "NHS",
            "url": "https://example.com/news5",
            "published_date": "2024-01-11T11:30:00Z",
            "category": "Clinical"
        }
    ]

def store_news_article(article_data: Dict[str, Any]) -> int:
    """Store a news article in the database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extract fields from article data
        title = article_data.get('title', '')
        summary = article_data.get('summary', '')
        content = article_data.get('content', '')
        url = article_data.get('url', '')
        source = article_data.get('source', 'Unknown')
        category = article_data.get('category', 'General')
        published_date = article_data.get('published_date')
        
        # Insert article into database
        cursor.execute("""
            INSERT INTO chatbot.news_articles 
            (title, summary, content, url, source, category, published_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (title, summary, content, url, source, category, published_date))
        
        article_id = cursor.fetchone()[0]
        conn.commit()
        
        logger.info(f"Stored news article: {title} (ID: {article_id})")
        return article_id
        
    except Exception as e:
        logger.error(f"Error storing news article: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ChatGPT-like response templates
RESPONSE_TEMPLATES = {
    "greeting": [
        "Hello! I'm RWA Adele, your intelligent assistant for finding pharmacy reports. How can I help you today?",
        "Hi there! I'm here to help you find the right pharmacy reports and data. What are you looking for?",
        "Welcome! I'm RWA Adele, your personal intelligence assistant for RWA Reports. What can I help you discover today?",
        "Good to see you! I'm here to help you navigate through our pharmacy reports. What information do you need?"
    ],
    "found_results": [
        "I found some great reports for you! Here's what I discovered:",
        "Perfect! I've located some relevant pharmacy reports that match your query:",
        "Great question! I found several reports that should help you:",
        "Excellent! Here are the reports I found that relate to your search:",
        "I've got some useful reports for you! Take a look at these:"
    ],
    "no_results": [
        "I couldn't find any reports matching that search. Could you try different keywords or be more specific?",
        "Hmm, I don't see any reports that match your query. Maybe try searching for related terms?",
        "I didn't find any results for that search. Would you like to try a different approach?",
        "No reports found for that query. Let me know if you'd like to search for something else!"
    ],
    "follow_up": [
        "Is there anything specific about these reports you'd like to know more about?",
        "Would you like me to explain any of these reports in more detail?",
        "Do any of these reports look like what you were searching for?",
        "Feel free to ask me about any of these reports or search for something else!"
    ]
}

def generate_chat_response(query: str, results: List[Dict[str, Any]], conversation_history: List[Dict[str, str]] = None) -> str:
    """Generate an intelligent ChatGPT-like conversational response with context"""
    
    query_lower = query.lower()
    
    # Check for ambiguous references that need clarification
    ambiguous_references = any(phrase in query_lower for phrase in ["it", "this", "that", "the module", "the report", "details on it", "tell me about it", "explain it"])
    
    if ambiguous_references:
        return handle_ambiguous_reference(query, conversation_history)
    
    # Check if user is asking for details about a specific module
    asking_for_details = any(phrase in query_lower for phrase in ["what is", "tell me about", "explain", "describe", "about this", "what does this", "in this report", "details about"])
    
    # If asking for details and we have results, provide detailed response
    if asking_for_details and results:
        return generate_detailed_module_response(results[0])
    
    # Check if it's a greeting
    greeting_words = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
    if any(word in query_lower for word in greeting_words):
        return random.choice(RESPONSE_TEMPLATES["greeting"])
    
    # Check if it's a thank you
    if any(word in query_lower for word in ["thank", "thanks", "appreciate"]):
        return "You're very welcome! I'm here whenever you need help finding pharmacy reports. Is there anything else I can help you with?"
    
    # Check if user is asking for general help or overview
    if any(phrase in query_lower for phrase in ["what can you do", "help me", "what reports", "show me all", "list all"]):
        return generate_overview_response(results)
    
    # Check if user is asking about a specific module/report
    if any(phrase in query_lower for phrase in ["what is", "tell me about", "explain", "describe", "about the"]):
        return generate_specific_module_response(query, results)
    
    # Check if user is looking for something specific
    if any(phrase in query_lower for phrase in ["find", "search", "where is", "how do i", "need"]):
        return generate_search_response(query, results)
    
    # Generate response based on results
    if not results:
        return generate_no_results_response(query)
    
    # Default intelligent response
    return generate_intelligent_response(query, results)

def generate_overview_response(results: List[Dict[str, Any]]) -> str:
    """Generate an overview of available reports"""
    if not results:
        return "I can help you find pharmacy reports! Here are the main categories available:\n\n• **Financial Reports** - Sales, margins, reimbursements\n• **Patient Reports** - Profiling, compliance, deliveries\n• **Product Reports** - Dispensing, stock, compliance\n• **Operational Reports** - Staff productivity, workflows\n• **Clinical Reports** - MUR, NMS, health services\n\nWhat specific area are you interested in?"
    
    # Group results by project
    projects = {}
    for result in results:
        project_name = result.get('project_name', 'Other')
        if project_name not in projects:
            projects[project_name] = []
        projects[project_name].append(result)
    
    response_parts = ["Here are the main report categories I can help you with:\n"]
    
    for project_name, workbooks in projects.items():
        response_parts.append(f"**{project_name}** ({len(workbooks)} reports)")
        for workbook in workbooks[:3]:  # Show first 3
            response_parts.append(f"  • {workbook.get('title', 'Untitled')}")
        if len(workbooks) > 3:
            response_parts.append(f"  • ... and {len(workbooks) - 3} more")
        response_parts.append("")
    
    response_parts.append("What specific report or category would you like to know more about?")
    
    return "\n".join(response_parts)

def generate_specific_module_response(query: str, results: List[Dict[str, Any]]) -> str:
    """Generate detailed information about a specific module"""
    if not results:
        return "I couldn't find that module. Try checking the sidebar for available reports."
    
    # Find the most relevant result
    best_match = results[0]
    title = best_match.get('title', 'Untitled')
    description = best_match.get('description', '')
    project_name = best_match.get('project_name', 'Unknown Project')
    
    # Check if user is asking for details (more comprehensive response)
    query_lower = query.lower()
    asking_for_details = any(phrase in query_lower for phrase in ["details", "tell me about", "explain", "describe", "what is"])
    
    # Try to parse rich description if it's JSON
    rich_description = None
    if description:
        try:
            import json
            rich_description = json.loads(description)
        except:
            pass
    
    # Generate detailed response if user asks for details
    if asking_for_details:
        return generate_detailed_module_response(best_match)
    
    # Generate a short, clean summary for other queries
    if rich_description and isinstance(rich_description, dict):
        # Extract just the overview/purpose for short response
        overview = rich_description.get('detailed_description', '')
        if overview:
            # Take only the first sentence or two for brevity
            sentences = overview.split('. ')
            short_desc = '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else overview
            return f"**{title}**\n\n{short_desc}\n\n*({project_name})*"
    
    # Fallback to basic description
    if description and len(description) > 50:
        # Truncate long descriptions
        short_desc = description[:100] + "..." if len(description) > 100 else description
        return f"**{title}**\n\n{short_desc}\n\n*({project_name})*"
    
    # Generate basic response
    title_lower = title.lower()
    if any(word in title_lower for word in ["financial", "sales", "margin"]):
        category = "financial performance"
    elif any(word in title_lower for word in ["patient", "customer"]):
        category = "patient management"
    elif any(word in title_lower for word in ["product", "dispensing"]):
        category = "product operations"
    elif any(word in title_lower for word in ["clinical", "mur", "nms"]):
        category = "clinical services"
    else:
        category = "pharmacy operations"
    
    return f"**{title}**\n\nProvides insights into {category} and reporting.\n\n*({project_name})*"

def handle_ambiguous_reference(query: str, conversation_history: List[Dict[str, str]] = None) -> str:
    """Handle ambiguous references like 'it', 'this', 'that' by asking for clarification"""
    
    if not conversation_history:
        return "I'd be happy to help! Could you please specify which module or report you'd like details about? You can mention the module number (like 2.30) or describe what you're looking for."
    
    # Extract recently mentioned modules from conversation history
    recent_modules = []
    
    # Look through the last 6 messages for module references
    for msg in reversed(conversation_history[-6:]):
        if msg.get("role") == "assistant" and msg.get("content"):
            content = msg["content"]
            # Look for module patterns like "2.30", "13.20", etc.
            import re
            module_pattern = r'(\d+\.\d+)'
            matches = re.findall(module_pattern, content)
            for match in matches:
                if match not in [m[0] for m in recent_modules]:
                    # Try to extract the full title with better pattern
                    title_pattern = rf'{re.escape(match)}[^\n]*?(?=\n|$|\(|\*|$)'
                    title_match = re.search(title_pattern, content)
                    if title_match:
                        title = title_match.group(0).strip()
                        # Clean up the title
                        title = re.sub(r'\*\*([^*]+)\*\*', r'\1', title)  # Remove bold formatting
                        title = re.sub(r'\([^)]+\)', '', title)  # Remove parenthetical info
                        title = title.strip()
                    else:
                        title = f"{match} Module"
                    recent_modules.append((match, title))
    
    # Also look for modules mentioned by the user
    for msg in reversed(conversation_history[-6:]):
        if msg.get("role") == "user" and msg.get("content"):
            content = msg["content"]
            import re
            module_pattern = r'(\d+\.\d+)'
            matches = re.findall(module_pattern, content)
            for match in matches:
                if match not in [m[0] for m in recent_modules]:
                    recent_modules.append((match, f"{match} Module"))
    
    if not recent_modules:
        return "I'd be happy to help! Could you please specify which module or report you'd like details about? You can mention the module number (like 2.30) or describe what you're looking for."
    
    # Generate helpful clarification response
    if len(recent_modules) == 1:
        module_num, title = recent_modules[0]
        return f"Are you asking about **{title}** that we discussed? I'd be happy to provide more details about it!"
    elif len(recent_modules) == 2:
        module1, title1 = recent_modules[0]
        module2, title2 = recent_modules[1]
        return f"Are you looking for details about **{title1}** or **{title2}** that we discussed previously? Or something else?"
    else:
        # Show the most recent modules
        recent_titles = [f"**{title}**" for _, title in recent_modules[:3]]
        if len(recent_modules) > 3:
            recent_titles.append("or another module")
        
        return f"Which module would you like details about? We recently discussed {', '.join(recent_titles)}. Please specify the module number or name."

def generate_detailed_module_response(result: Dict[str, Any]) -> str:
    """Generate detailed response about any module when user asks for details"""
    title = result.get('title', 'Unknown Module')
    description = result.get('description', '')
    project_name = result.get('project_name', 'Unknown')
    
    # Try to parse rich description
    if description:
        try:
            import json
            rich_desc = json.loads(description)
            if isinstance(rich_desc, dict):
                response_parts = [f"**{title}**\n"]
                
                # Add detailed description
                if rich_desc.get('detailed_description'):
                    response_parts.append(f"{rich_desc['detailed_description']}\n")
                
                # Add purpose
                if rich_desc.get('purpose'):
                    response_parts.append(f"**Purpose:**\n{rich_desc['purpose']}\n")
                
                # Add key metrics
                if rich_desc.get('key_metrics'):
                    metrics = rich_desc['key_metrics']
                    if isinstance(metrics, list):
                        response_parts.append(f"**Key Metrics:**\n")
                        for metric in metrics:
                            response_parts.append(f"• {metric}")
                        response_parts.append("")
                
                # Add usage notes
                if rich_desc.get('usage_notes'):
                    response_parts.append(f"**How to Use:**\n{rich_desc['usage_notes']}\n")
                
                # Add target audience
                if rich_desc.get('target_audience'):
                    response_parts.append(f"**Target Audience:**\n{rich_desc['target_audience']}\n")
                
                response_parts.append(f"*({project_name})*")
                return "\n".join(response_parts)
        except Exception as e:
            print(f"Error parsing rich description: {e}")
            pass
    
    # Fallback: Generate intelligent response based on module title and type
    title_lower = title.lower()
    
    # Determine module category and generate appropriate description
    if any(word in title_lower for word in ["financial", "sales", "margin", "revenue", "cost"]):
        category = "financial performance and reporting"
        purpose = "tracks financial metrics, sales data, margins, and revenue analysis"
    elif any(word in title_lower for word in ["patient", "care", "service", "clinical", "nms", "mur"]):
        category = "patient care and clinical services"
        purpose = "monitors patient care delivery, clinical services, and health outcomes"
    elif any(word in title_lower for word in ["stock", "inventory", "product", "dispensing"]):
        category = "inventory and product management"
        purpose = "manages stock levels, product performance, and dispensing operations"
    elif any(word in title_lower for word in ["staff", "productivity", "performance", "management"]):
        category = "staff performance and management"
        purpose = "tracks staff productivity, performance metrics, and operational efficiency"
    elif any(word in title_lower for word in ["compliance", "regulatory", "audit", "quality"]):
        category = "compliance and quality assurance"
        purpose = "ensures regulatory compliance, quality standards, and audit requirements"
    else:
        category = "pharmacy operations and reporting"
        purpose = "provides insights into pharmacy operations and performance"
    
    return f"**{title}**\n\nThis module focuses on {category}. It {purpose} to help optimize pharmacy operations and decision-making.\n\n*({project_name})*"

def generate_detailed_services_response(result: Dict[str, Any]) -> str:
    """Generate detailed response about Weekly Services Report"""
    title = result.get('title', 'Weekly Services Report')
    return f"**{title}**\n\nProvides weekly insights into patient care services including MURs, NMS consultations, clinical services, and staff productivity metrics.\n\n*Helps track service delivery and identify areas for improvement.*"

def generate_detailed_executive_response(result: Dict[str, Any]) -> str:
    """Generate detailed response about Executive Report"""
    title = result.get('title', 'Executive Monthly Report')
    return f"**{title}**\n\nHigh-level monthly summary for senior management covering financial performance, operational KPIs, strategic initiatives, and market analysis.\n\n*Essential for board presentations and strategic decision-making.*"

def generate_search_response(query: str, results: List[Dict[str, Any]]) -> str:
    """Generate response for search queries"""
    if not results:
        return f"I couldn't find any reports matching '{query}'. Try checking the sidebar for available categories or rephrasing your search."
    
    response_parts = [f"I found {len(results)} report(s) related to '{query}':\n"]
    
    for i, result in enumerate(results, 1):
        title = result.get('title', 'Untitled')
        description = result.get('description', '')
        project_name = result.get('project_name', 'Unknown')
        
        result_text = f"**{title}**"
        if description:
            result_text += f" - {description}"
        result_text += f" ({project_name})"
        
        response_parts.append(f"{i}. {result_text}")
    
    response_parts.append("\nWould you like more details about any of these reports?")
    
    return "\n".join(response_parts)

def generate_no_results_response(query: str) -> str:
    """Generate response when no results are found"""
    return f"I couldn't find any reports matching '{query}'. Here are some suggestions:\n\n• Check the sidebar for available report categories\n• Try searching for broader terms like 'financial', 'patient', or 'product'\n• Ask me about specific report types like 'MUR reports' or 'sales data'\n\nWhat would you like to explore?"

def generate_intelligent_response(query: str, results: List[Dict[str, Any]]) -> str:
    """Generate an intelligent response based on query and results"""
    if not results:
        return generate_no_results_response(query)
    
    # Analyze the query to determine intent
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["list", "show", "all", "available"]):
        return generate_overview_response(results)
    
    # Show all results with clean formatting
    response_parts = [f"Found {len(results)} relevant reports:\n"]
    
    for i, result in enumerate(results, 1):
        title = result.get('title', 'Untitled')
        project_name = result.get('project_name', 'Unknown')
        
        response_parts.append(f"**{i}. {title}**")
        response_parts.append(f"   *({project_name})*")
        
        if i < len(results):
            response_parts.append("")
    
    response_parts.append("\nAsk about any specific report for details!")
    
    return "\n".join(response_parts)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "RWA Adele Enhanced Chat API", "status": "running"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chatbot.objects")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy",
            "api_type": "enhanced_chat_with_semantic_search",
            "database_connected": True,
            "total_records": count,
            "features": ["semantic_search", "chatgpt_responses", "conversation_context"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "api_type": "enhanced_chat_with_semantic_search",
            "database_connected": False,
            "error": str(e)
        }

@app.get("/workbooks")
async def get_workbooks_endpoint():
    """Get all workbooks"""
    try:
        workbooks = get_workbooks()
        return {"workbooks": workbooks, "count": len(workbooks)}
    except Exception as e:
        logger.error(f"Error getting workbooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects")
async def get_projects_endpoint():
    """Get all projects with their workbooks"""
    try:
        logger.info("Projects endpoint called")
        projects = get_projects()
        logger.info(f"Returning {len(projects)} projects to client")
        return {"projects": projects, "count": len(projects)}
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news")
async def get_news_endpoint():
    """Get latest news articles from n8n workflow"""
    try:
        logger.info("News endpoint called")
        news = get_latest_news()
        logger.info(f"Returning {len(news)} news articles to client")
        return {"news": news, "count": len(news)}
    except Exception as e:
        logger.error(f"Error getting news: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news/webhook")
async def news_webhook_endpoint(request: Dict[str, Any]):
    """Webhook endpoint for n8n to send news articles"""
    try:
        logger.info("News webhook called")
        
        # Extract article data from request
        article_data = request.get("article", {})
        if not article_data:
            raise HTTPException(status_code=400, detail="No article data provided")
        
        # Store article in database
        article_id = store_news_article(article_data)
        
        logger.info(f"Stored news article with ID: {article_id}")
        return {"status": "success", "article_id": article_id, "message": "Article stored successfully"}
        
    except Exception as e:
        logger.error(f"Error storing news article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_endpoint(request: Dict[str, Any]):
    """Search for content with ChatGPT-like responses"""
    try:
        query = request.get("query", "")
        limit = request.get("limit", 10)
        conversation_history = request.get("conversation_history", [])
        
        if not query:
            return {"results": [], "count": 0, "message": "No query provided"}
        
        # Search for content
        results = search_content_semantic(query, limit)
        
        # Generate ChatGPT-like response
        chat_response = generate_chat_response(query, results, conversation_history)
        
        return {
            "results": results,
            "count": len(results),
            "query": query,
            "chat_response": chat_response,
            "search_type": "semantic",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_endpoint(request: Dict[str, Any]):
    """Enhanced chat endpoint with AI agent"""
    try:
        message = request.get("message", "")
        conversation_history = request.get("conversation_history", [])
        use_agent = request.get("use_agent", True)  # Default to using agent
        
        if not message:
            return {"response": "I didn't receive a message. Could you please try again?", "conversation_history": conversation_history}
        
        # Try to use AI agent first
        if use_agent:
            agent_instance = get_agent()
            if agent_instance:
                try:
                    result = agent_instance.chat(message, conversation_history)
                    return {
                        "response": result["response"],
                        "results": [],
                        "conversation_history": result["conversation_history"],
                        "timestamp": datetime.now().isoformat(),
                        "agent_used": True
                    }
                except Exception as e:
                    logger.error(f"Agent error: {e}, falling back to simple search")
                    # Fall back to simple search if agent fails
        
        # Fallback to original logic with better grounding
        # Check for ambiguous references first, before searching
        message_lower = message.lower()
        ambiguous_references = any(phrase in message_lower for phrase in ["it", "this", "that", "the module", "the report", "details on it", "tell me about it", "explain it"])
        
        if ambiguous_references:
            chat_response = handle_ambiguous_reference(message, conversation_history)
            # Update conversation history
            conversation_history.append({"role": "user", "content": message})
            conversation_history.append({"role": "assistant", "content": chat_response})
            
            return {
                "response": chat_response,
                "results": [],
                "conversation_history": conversation_history,
                "timestamp": datetime.now().isoformat(),
                "agent_used": False
            }
        
        # Search for content
        results = search_content_semantic(message, 5)
        
        # Generate ChatGPT-like response with database grounding
        chat_response = generate_chat_response(message, results, conversation_history)
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": chat_response})
        
        return {
            "response": chat_response,
            "results": results,
            "conversation_history": conversation_history,
            "timestamp": datetime.now().isoformat(),
            "agent_used": False
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/news/{article_id}")
async def delete_news_article(article_id: int):
    """Delete a news article by ID"""
    try:
        logger.info(f"Deleting news article with ID: {article_id}")
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete the article
        cursor.execute("DELETE FROM news_articles WHERE id = %s", (article_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully deleted news article with ID: {article_id}")
        return {"status": "success", "message": f"Article {article_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting news article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/news/cleanup/test")
async def cleanup_test_articles():
    """Delete all test articles"""
    try:
        logger.info("Cleaning up test articles")
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete test articles (those with "test" in title or source)
        cursor.execute("""
            DELETE FROM news_articles 
            WHERE LOWER(title) LIKE '%test%' 
            OR LOWER(source) LIKE '%test%'
            OR LOWER(title) LIKE '%n8n%'
        """)
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} test articles")
        return {"status": "success", "message": f"Cleaned up {deleted_count} test articles"}
        
    except Exception as e:
        logger.error(f"Error cleaning up test articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting RWA Adele Enhanced Chat API...")
    print("📱 Frontend: http://localhost:3000")
    print("🔧 API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("✨ Features: ChatGPT-like responses, semantic search, conversation context")
    uvicorn.run(app, host="0.0.0.0", port=8000)
