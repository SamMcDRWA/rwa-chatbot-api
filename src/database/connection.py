"""
Database connection and configuration for RWA Chatbot Phase 1
Handles PostgreSQL connection with pgvector support
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging

logger = logging.getLogger(__name__)

# Database configuration - support both DATABASE_URL and individual parameters
def get_database_url():
    """Get database URL from environment variables"""
    # Check for DATABASE_URL first (preferred for production)
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        logger.info(f"Using DATABASE_URL: {database_url[:20]}...")
        return database_url
    
    # Fallback to individual parameters
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'rwa_chatbot'),
        'user': os.getenv('DB_USER', 'rwa_bot'),
        'password': os.getenv('DB_PASSWORD', '')
    }
    
    # Create database URL from individual parameters
    url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    logger.info(f"Using individual parameters: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    return url

# Initialize database URL (will be set when module is imported)
DATABASE_URL = None

# Create engine with SSL support for production databases
def create_database_engine():
    """Create database engine with appropriate configuration"""
    # Get the current database URL
    database_url = get_database_url()
    
    # Check if this is a cloud database (Supabase, etc.)
    is_cloud_db = any(host in database_url for host in ['supabase.co', 'amazonaws.com', 'azure.com', 'googleapis.com'])
    
    engine_kwargs = {
        'echo': False,
        'pool_pre_ping': True,  # Verify connections before use
        'pool_recycle': 3600,   # Recycle connections every hour
    }
    
    # Add SSL configuration for cloud databases
    if is_cloud_db:
        engine_kwargs['connect_args'] = {
            'sslmode': 'require',
            'sslcert': None,
            'sslkey': None,
            'sslrootcert': None
        }
        logger.info("Using SSL connection for cloud database")
    
    logger.info(f"Creating database engine for: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    return create_engine(database_url, **engine_kwargs)

# Create engine (will be created when needed)
engine = None

# Create base class for models
Base = declarative_base()


def get_engine():
    """Get database engine, creating it if necessary"""
    global engine
    if engine is None:
        engine = create_database_engine()
    return engine

def get_db():
    """Dependency to get database session"""
    db_engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    """
    Test database connection and verify pgvector extension
    
    Returns:
        bool: True if connection successful and pgvector available
    """
    try:
        db_engine = get_engine()
        with db_engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            
            # Check if pgvector extension is available
            result = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            if result.fetchone():
                logger.info("pgvector extension is available")
                return True
            else:
                logger.warning("pgvector extension not found. Please run setup_database.sql")
                return False
                
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def create_tables():
    """Create all tables defined in models"""
    try:
        db_engine = get_engine()
        Base.metadata.create_all(bind=db_engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False


def run_setup_script():
    """
    Run the database setup script to create schema and tables
    This should be run once to set up the database
    """
    try:
        db_engine = get_engine()
        with db_engine.connect() as conn:
            # Read and execute the setup script
            with open('setup_database.sql', 'r') as f:
                setup_sql = f.read()
            
            # Execute the script
            conn.execute(text(setup_sql))
            conn.commit()
            
        logger.info("Database setup script executed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to run database setup script: {e}")
        return False
