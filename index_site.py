"""
End-to-end indexer script for RWA Chatbot Phase 1
Indexes Tableau sites by fetching metadata and storing in database
"""

import os
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv
from src.tableau.enhanced_client import EnhancedTableauClient
from src.database.store import upsert_records_batch, get_record_count, get_embedding_stats
from src.tableau.quality_checks import QualityChecker, RateLimiter, PaginationHelper, validate_environment, get_indexing_recommendations

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def index_site(server_url: str, pat_name: str, pat_secret: str, site_name: str, 
               project_filter: str = None, object_types: list = None, 
               enable_quality_checks: bool = True, max_objects: int = None) -> Dict[str, int]:
    """
    Index a Tableau site
    
    Args:
        server_url: Tableau server URL
        pat_name: Personal Access Token name
        pat_secret: Personal Access Token secret
        site_name: Site name
        project_filter: Optional comma-separated project names to filter
        object_types: List of object types to index (workbooks, datasources, views)
        enable_quality_checks: Whether to run quality checks on records
        max_objects: Optional maximum number of objects to index
        
    Returns:
        Dictionary with indexing statistics
    """
    stats = {
        "workbooks": 0,
        "datasources": 0,
        "views": 0,
        "total_processed": 0,
        "errors": 0
    }
    
    try:
        # Create enhanced client
        logger.info(f"Creating Tableau client for site: {site_name}")
        client = EnhancedTableauClient(server_url, pat_name, pat_secret, site_name)
        
        # Authenticate
        logger.info("Authenticating with Tableau Server...")
        if not client.signin():
            logger.error("Failed to authenticate with Tableau Server")
            return stats
        
        site_id = client.get_site_id()
        logger.info(f"Successfully authenticated. Site ID: {site_id}")
        
        # Get initial record count
        initial_count = get_record_count(site_id)
        logger.info(f"Initial record count for site {site_id}: {initial_count}")
        
        # Fetch comprehensive metadata
        logger.info("Fetching comprehensive metadata...")
        if object_types:
            metadata = client.fetch_comprehensive_metadata(object_types)
        else:
            metadata = client.fetch_comprehensive_metadata()
        
        # Count objects by type
        workbooks = metadata.get("workbooks", [])
        datasources = metadata.get("datasources", [])
        views = metadata.get("views", [])
        
        logger.info(f"Retrieved metadata:")
        logger.info(f"  - {len(workbooks)} workbooks")
        logger.info(f"  - {len(datasources)} datasources")
        logger.info(f"  - {len(views)} views")
        
        # Process metadata for indexing
        logger.info("Processing metadata for database indexing...")
        records = client.prepare_objects_for_indexing(metadata)
        
        if not records:
            logger.warning("No records to index")
            return stats
        
        # Apply max_objects limit if specified
        if max_objects and len(records) > max_objects:
            logger.info(f"Limiting to {max_objects} objects (found {len(records)})")
            records = records[:max_objects]
        
        # Run quality checks if enabled
        quality_results = None
        if enable_quality_checks and records:  # Only run quality checks if we have records
            logger.info("Running quality checks...")
            try:
                quality_checker = QualityChecker(site_id, site_name)
                quality_results = quality_checker.run_all_checks(records)
                
                if not quality_results["overall_quality"]:
                    logger.error("Quality checks failed - critical issues found")
                    logger.error(f"Issues: {quality_results['issues']}")
                    stats["errors"] += 1
                    return stats
                
                if quality_results["warnings"]:
                    logger.warning(f"Quality warnings: {quality_results['warnings']}")
            except Exception as e:
                logger.warning(f"Quality checks failed, continuing without them: {e}")
                quality_results = None
        
        # Count records by type
        for record in records:
            obj_type = record.get("object_type", "unknown")
            if obj_type in stats:
                stats[obj_type] += 1
        
        stats["total_processed"] = len(records)
        
        # Upsert records to database
        logger.info(f"Upserting {len(records)} records to database...")
        try:
            processed_count = upsert_records_batch(records, batch_size=50)
            logger.info(f"Successfully processed {processed_count} records")
            
        except Exception as e:
            logger.error(f"Error during database upsert: {e}")
            stats["errors"] += 1
            return stats
        
        # Get final record count
        final_count = get_record_count(site_id)
        logger.info(f"Final record count for site {site_id}: {final_count}")
        logger.info(f"Added/updated {final_count - initial_count} records")
        
        # Get embedding statistics
        embedding_stats = get_embedding_stats()
        logger.info(f"Embedding statistics: {embedding_stats}")
        
        # Add quality results to stats
        if quality_results:
            stats["quality_results"] = quality_results
            stats["recommendations"] = get_indexing_recommendations(quality_results)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error during site indexing: {e}")
        stats["errors"] += 1
        return stats
    
    finally:
        # Clean up
        try:
            client.signout()
            logger.info("Signed out from Tableau Server")
        except:
            pass


def main():
    """Main function to run the indexer"""
    
    # Load environment variables
    load_dotenv()
    
    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed")
        return
    
    # Get configuration
    server_url = os.getenv('TABLEAU_SERVER_URL')
    pat_name = os.getenv('TABLEAU_PAT_NAME')
    pat_secret = os.getenv('TABLEAU_PAT_SECRET')
    site_name = os.getenv('TABLEAU_SITE_NAME')
    project_filter = os.getenv('TABLEAU_PROJECT_FILTER')
    
    # Parse project filter
    project_list = None
    if project_filter:
        project_list = [p.strip() for p in project_filter.split(",") if p.strip()]
        logger.info(f"Project filter: {project_list}")
    
    # Run indexing
    logger.info("Starting Tableau site indexing...")
    logger.info(f"Server: {server_url}")
    logger.info(f"Site: {site_name}")
    
    stats = index_site(server_url, pat_name, pat_secret, site_name, project_filter)
    
    # Print results
    print("\n" + "="*60)
    print("INDEXING RESULTS")
    print("="*60)
    print(f"Workbooks indexed: {stats['workbooks']}")
    print(f"Datasources indexed: {stats['datasources']}")
    print(f"Views indexed: {stats['views']}")
    print(f"Total records processed: {stats['total_processed']}")
    print(f"Errors: {stats['errors']}")
    
    # Print quality results if available
    if 'quality_results' in stats:
        quality = stats['quality_results']
        print(f"\nQuality Check Results:")
        print(f"  Overall Quality: {'✅ PASS' if quality['overall_quality'] else '❌ FAIL'}")
        print(f"  Issues: {len(quality['issues'])}")
        print(f"  Warnings: {len(quality['warnings'])}")
        
        if quality['warnings']:
            print(f"\nQuality Warnings:")
            for warning in quality['warnings'][:5]:  # Show first 5 warnings
                print(f"  - {warning}")
            if len(quality['warnings']) > 5:
                print(f"  ... and {len(quality['warnings']) - 5} more warnings")
    
    # Print recommendations if available
    if 'recommendations' in stats and stats['recommendations']:
        print(f"\nRecommendations:")
        for rec in stats['recommendations']:
            print(f"  - {rec}")
    
    if stats['errors'] == 0:
        print("\n✅ Indexing completed successfully!")
    else:
        print(f"\n⚠️  Indexing completed with {stats['errors']} errors")
    
    print("\nNext steps:")
    print("1. Run 'python embed.py' to generate vector embeddings")
    print("2. Test search functionality")
    print("3. Verify records in database: SELECT COUNT(*) FROM chatbot.objects;")


if __name__ == "__main__":
    main()
