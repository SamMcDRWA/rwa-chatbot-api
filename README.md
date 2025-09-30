# RWA Chatbot Phase 1

A chatbot that helps customers find Tableau modules by answering "Where can I find X" questions.

## Setup

1. Create and activate virtual environment:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\Activate.ps1
# On Unix/Mac:
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
   - Copy `.env` template and fill in your Tableau and database credentials
   - Never commit the actual `.env` file with secrets

## Project Structure

- `src/` - Main application code
- `src/tableau/` - Tableau API integration
  - `client.py` - REST API client
  - `metadata_client.py` - GraphQL metadata client
  - `enhanced_client.py` - Combined client with both APIs
- `src/search/` - Search and indexing functionality
- `src/database/` - Database models and operations
- `src/api/` - FastAPI endpoints
- `examples/` - Usage examples and demonstrations

## Features

- **Tableau Integration**: REST API and GraphQL metadata client
- **Comprehensive Indexing**: Workbooks, dashboards, datasources, and views
- **Semantic Search**: Using sentence transformers and vector embeddings
- **Database Storage**: PostgreSQL with pgvector for vector similarity search
- **FastAPI Interface**: RESTful API for chatbot queries
- **Metadata Rich**: Tags, descriptions, fields, owners, and project information
