"""
Database setup script for RWA Chatbot Phase 1
Run this script to set up the PostgreSQL database with pgvector extension

Supports both individual database parameters and DATABASE_URL format.
"""

import os
import logging
import urllib.parse
from dotenv import load_dotenv
from src.database.connection import test_connection, run_setup_script

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_database_config():
    """Validate database configuration from environment variables"""
    
    # Check for DATABASE_URL first (preferred for production)
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        try:
            # Validate DATABASE_URL format
            parsed = urllib.parse.urlparse(database_url)
            if parsed.scheme not in ['postgresql', 'postgres']:
                raise ValueError("DATABASE_URL must use postgresql:// or postgres:// scheme")
            
            logger.info("Using DATABASE_URL for database connection")
            return True, "DATABASE_URL"
        except Exception as e:
            logger.error(f"Invalid DATABASE_URL format: {e}")
            return False, f"Invalid DATABASE_URL: {e}"
    
    # Fallback to individual parameters
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        return False, f"Missing required environment variables: {missing_vars}"
    
    # Check if credentials are still placeholder values
    password = os.getenv('DB_PASSWORD', '')
    if password in ["***redacted***", "", "your_secure_password_here", "your_supabase_password_here"]:
        return False, "Please update your .env file with actual database credentials"
    
    logger.info("Using individual database parameters for connection")
    return True, "individual_params"

def setup_database():
    """Set up the database with schema and tables"""
    
    # Load environment variables
    load_dotenv()
    
    print("🚀 RWA Chatbot Phase 1 - Database Setup")
    print("=" * 60)
    
    # Validate database configuration
    is_valid, config_type = validate_database_config()
    if not is_valid:
        print(f"❌ Configuration Error: {config_type}")
        print("\n📋 Required Configuration:")
        print("Option 1 - DATABASE_URL (Recommended for production):")
        print("  DATABASE_URL=postgresql://user:password@host:port/database")
        print("\nOption 2 - Individual Parameters:")
        print("  DB_HOST=your_host")
        print("  DB_PORT=5432")
        print("  DB_NAME=your_database")
        print("  DB_USER=your_user")
        print("  DB_PASSWORD=your_password")
        print("\n💡 For Supabase: Use the connection string from your project settings")
        return False
    
    try:
        # Test basic connection
        print("🔌 Testing database connection...")
        if not test_connection():
            print("❌ Database connection failed")
            print("\n🔧 Troubleshooting:")
            print("1. Check your database credentials")
            print("2. Ensure PostgreSQL is running")
            print("3. Verify network connectivity")
            print("4. Check firewall settings")
            if config_type == "individual_params":
                print("5. Try using DATABASE_URL instead")
            return False
        
        print("✅ Database connection successful")
        
        # Run setup script
        print("📋 Setting up database schema and tables...")
        if not run_setup_script():
            print("❌ Database setup script failed")
            print("\n🔧 Troubleshooting:")
            print("1. Check if you have CREATE privileges")
            print("2. Verify pgvector extension is available")
            print("3. Check database logs for errors")
            return False
        
        print("✅ Database schema and tables created successfully")
        
        # Verify setup
        print("🔍 Verifying database setup...")
        if not test_connection():
            print("❌ Database verification failed")
            print("Setup completed but verification failed - check database logs")
            return False
        
        print("✅ Database verification successful")
        
        # Show configuration summary
        print(f"\n📊 Configuration Summary:")
        print(f"   Connection Method: {config_type}")
        if config_type == "DATABASE_URL":
            database_url = os.getenv('DATABASE_URL')
            # Mask password in URL
            if database_url:
                parsed = urllib.parse.urlparse(database_url)
                masked_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
                print(f"   Database URL: {masked_url}")
        else:
            print(f"   Host: {os.getenv('DB_HOST')}")
            print(f"   Port: {os.getenv('DB_PORT')}")
            print(f"   Database: {os.getenv('DB_NAME')}")
            print(f"   User: {os.getenv('DB_USER')}")
        
        print("\n🎉 Database setup complete!")
        print("Your database is ready for the RWA Chatbot Phase 1 application.")
        print("\n📋 Next steps:")
        print("1. Run: python index_site.py")
        print("2. Run: python embed.py")
        print("3. Run: python main.py")
        
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        print(f"❌ Database setup failed with error: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your .env file configuration")
        print("2. Verify database server is accessible")
        print("3. Check database logs for detailed error messages")
        return False

if __name__ == "__main__":
    success = setup_database()
    
    if not success:
        print("\n❌ Setup failed. Please check the errors above and try again.")
        exit(1)
    else:
        print("\n✅ Setup completed successfully!")
        print("You can now run the application with: python main.py")
