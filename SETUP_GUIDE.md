# RWA Chatbot Phase 1 - Setup Guide

This guide will help you set up the RWA Chatbot Phase 1 project with PostgreSQL and Tableau integration.

## Prerequisites

1. **Python 3.10+** installed
2. **PostgreSQL 14+** with pgvector extension
3. **Tableau Server** access with admin privileges
4. **Personal Access Token (PAT)** for Tableau Server

## Step 1: Database Setup

### 1.1 Install PostgreSQL with pgvector

**Option A: Using Docker (Recommended for development)**
```bash
# Pull PostgreSQL with pgvector
docker pull pgvector/pgvector:pg16

# Run PostgreSQL container
docker run --name rwa-chatbot-db \
  -e POSTGRES_DB=rwa_chatbot \
  -e POSTGRES_USER=rwa_bot \
  -e POSTGRES_PASSWORD=your_secure_password \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16
```

**Option B: Local Installation**
1. Install PostgreSQL 14+ from [postgresql.org](https://www.postgresql.org/download/)
2. Install pgvector extension:
   ```bash
   # On Ubuntu/Debian
   sudo apt install postgresql-14-pgvector
   
   # On macOS with Homebrew
   brew install pgvector
   
   # On Windows, download from pgvector releases
   ```

### 1.2 Create Database and Schema

1. Connect to your PostgreSQL instance
2. Run the setup script:
   ```bash
   psql -h localhost -U rwa_bot -d rwa_chatbot -f setup_database.sql
   ```

### 1.3 Test Database Connection

```bash
python test_database.py
```

## Step 2: Tableau Configuration

### 2.1 Create Personal Access Token

1. Log into your Tableau Server as an admin
2. Go to **My Account** → **Personal Access Tokens**
3. Click **Create Token**
4. Set:
   - **Token Name**: `svc_rwa_chatbot`
   - **Site**: Select your target site
   - **Expiration**: Set appropriate expiration date
5. Copy the **Token Secret** (you won't see it again!)

### 2.2 Get Site Information

1. Note your **Site Name** (content URL)
2. Note your **Server URL** (e.g., `https://your-tableau-server.com`)

### 2.3 Update Environment Variables

Edit your `.env` file with actual values:

```env
# Tableau Configuration
TABLEAU_SERVER_URL=https://your-tableau-server.com
TABLEAU_PAT_NAME=svc_rwa_chatbot
TABLEAU_PAT_SECRET=your_actual_token_secret_here
TABLEAU_SITE_NAME=your_site_name
TABLEAU_PROJECT_FILTER=                    # optional: comma-separated project names

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rwa_chatbot
DB_USER=rwa_bot
DB_PASSWORD=your_secure_password
```

### 2.4 Test Tableau Connection

```bash
python test_tableau_client.py
```

## Step 3: Verify Complete Setup

### 3.1 Start the Application

```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows
# or
source .venv/bin/activate   # Linux/Mac

# Start the application
python main.py
```

### 3.2 Test Endpoints

1. **Health Check**: http://localhost:8000/
2. **Detailed Health**: http://localhost:8000/health
3. **API Documentation**: http://localhost:8000/docs

## Step 4: Next Steps

Once your setup is complete, you can:

1. **Index Tableau Content**: Build the crawler to populate the database
2. **Implement Search**: Add semantic search capabilities
3. **Create Chat Interface**: Build the chatbot API endpoints

## Troubleshooting

### Database Issues

- **Connection Refused**: Check if PostgreSQL is running and accessible
- **pgvector not found**: Ensure pgvector extension is installed
- **Permission Denied**: Check database user permissions

### Tableau Issues

- **Authentication Failed**: Verify PAT credentials and site name
- **API Errors**: Check Tableau Server version compatibility
- **Rate Limiting**: Implement proper delays between API calls

### Common Solutions

1. **Check logs**: Look at console output for detailed error messages
2. **Verify credentials**: Ensure all environment variables are correct
3. **Test connectivity**: Use the test scripts to isolate issues
4. **Check versions**: Ensure compatibility between components

## Security Notes

- Never commit `.env` files with real credentials
- Use strong passwords for database
- Rotate Tableau PATs regularly
- Consider using environment-specific configurations

## Support

If you encounter issues:

1. Check the logs for error messages
2. Verify all prerequisites are met
3. Test individual components using the test scripts
4. Review the troubleshooting section above
