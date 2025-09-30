"""
Embedding generation module for RWA Chatbot Phase 1
Generates vector embeddings for Tableau objects using sentence transformers
"""

import os
import logging
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from dotenv import load_dotenv
from src.database.connection import get_engine

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2


def load_model() -> SentenceTransformer:
    """
    Load the sentence transformer model
    
    Returns:
        Loaded SentenceTransformer model
    """
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    try:
        model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


def get_unembedded_records(limit: int = None) -> List[Dict[str, Any]]:
    """
    Get records that don't have embeddings yet
    
    Args:
        limit: Optional limit on number of records to fetch
        
    Returns:
        List of record dictionaries
    """
    engine = get_engine()
    
    query = """
        SELECT id, text_blob, title, object_type 
        FROM chatbot.objects 
        WHERE embedding IS NULL
        ORDER BY updated_at DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text(query)).fetchall()
            
            records = []
            for row in result:
                records.append({
                    "id": row[0],
                    "text_blob": row[1],
                    "title": row[2],
                    "object_type": row[3]
                })
            
            logger.info(f"Found {len(records)} records without embeddings")
            return records
            
    except Exception as e:
        logger.error(f"Database error getting unembedded records: {e}")
        raise


def generate_embeddings(texts: List[str], model: SentenceTransformer) -> List[List[float]]:
    """
    Generate embeddings for a list of texts
    
    Args:
        texts: List of text strings to embed
        model: SentenceTransformer model
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    logger.info(f"Generating embeddings for {len(texts)} texts")
    
    try:
        # Generate embeddings with normalization
        embeddings = model.encode(
            texts, 
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=32
        )
        
        # Convert to list of lists
        embeddings_list = [emb.tolist() for emb in embeddings]
        
        logger.info(f"Generated {len(embeddings_list)} embeddings")
        return embeddings_list
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise


def update_embeddings(records: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
    """
    Update database records with their embeddings
    
    Args:
        records: List of record dictionaries
        embeddings: List of embedding vectors
        
    Returns:
        Number of records updated
    """
    if len(records) != len(embeddings):
        raise ValueError("Number of records and embeddings must match")
    
    engine = get_engine()
    updated_count = 0
    
    try:
        with engine.begin() as conn:
            for record, embedding in zip(records, embeddings):
                try:
                    # Update record with embedding
                    update_query = text("""
                        UPDATE chatbot.objects 
                        SET embedding = :embedding::vector 
                        WHERE id = :id
                    """)
                    
                    conn.execute(update_query, {
                        "embedding": embedding,
                        "id": record["id"]
                    })
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to update embedding for record {record['id']}: {e}")
                    continue
        
        logger.info(f"Updated {updated_count} records with embeddings")
        return updated_count
        
    except Exception as e:
        logger.error(f"Database error updating embeddings: {e}")
        raise


def embed_all(limit: int = None, batch_size: int = 100) -> Dict[str, int]:
    """
    Generate embeddings for all unembedded records
    
    Args:
        limit: Optional limit on number of records to process
        batch_size: Number of records to process per batch
        
    Returns:
        Dictionary with processing statistics
    """
    stats = {
        "total_records": 0,
        "processed_records": 0,
        "errors": 0
    }
    
    try:
        # Load model
        model = load_model()
        
        # Get unembedded records
        records = get_unembedded_records(limit)
        stats["total_records"] = len(records)
        
        if not records:
            logger.info("No records to embed")
            return stats
        
        logger.info(f"Processing {len(records)} records in batches of {batch_size}")
        
        # Process in batches
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(records) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} records)")
            
            try:
                # Extract texts
                texts = [record["text_blob"] for record in batch]
                
                # Generate embeddings
                embeddings = generate_embeddings(texts, model)
                
                # Update database
                updated = update_embeddings(batch, embeddings)
                stats["processed_records"] += updated
                
                logger.info(f"Batch {batch_num} completed: {updated} records updated")
                
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                stats["errors"] += 1
                continue
        
        logger.info(f"Embedding process completed: {stats['processed_records']}/{stats['total_records']} records processed")
        return stats
        
    except Exception as e:
        logger.error(f"Error during embedding process: {e}")
        stats["errors"] += 1
        return stats


def verify_embeddings() -> Dict[str, Any]:
    """
    Verify embedding quality and statistics
    
    Returns:
        Dictionary with verification statistics
    """
    engine = get_engine()
    
    try:
        with engine.begin() as conn:
            # Get embedding statistics
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(embedding) as records_with_embeddings,
                    AVG(array_length(embedding, 1)) as avg_embedding_dimension,
                    MIN(array_length(embedding, 1)) as min_embedding_dimension,
                    MAX(array_length(embedding, 1)) as max_embedding_dimension
                FROM chatbot.objects
            """)
            
            result = conn.execute(stats_query).fetchone()
            
            if result:
                stats = {
                    "total_records": result[0],
                    "records_with_embeddings": result[1],
                    "records_without_embeddings": result[0] - result[1],
                    "embedding_percentage": (result[1] / result[0] * 100) if result[0] > 0 else 0,
                    "avg_embedding_dimension": float(result[2]) if result[2] else 0,
                    "min_embedding_dimension": result[3],
                    "max_embedding_dimension": result[4]
                }
                
                # Check if dimensions match expected
                if stats["avg_embedding_dimension"] != EMBEDDING_DIMENSION:
                    logger.warning(f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {stats['avg_embedding_dimension']}")
                
                return stats
            else:
                return {"error": "No data found"}
                
    except Exception as e:
        logger.error(f"Error verifying embeddings: {e}")
        raise


def main():
    """Main function to run embedding generation"""
    
    print("RWA Chatbot Phase 1 - Embedding Generation")
    print("=" * 50)
    
    try:
        # Check if there are records to embed
        records = get_unembedded_records(limit=1)
        if not records:
            print("No records found that need embeddings")
            return
        
        # Get total count
        total_records = get_unembedded_records()
        print(f"Found {len(total_records)} records that need embeddings")
        
        # Run embedding process
        stats = embed_all()
        
        # Print results
        print("\n" + "="*50)
        print("EMBEDDING RESULTS")
        print("="*50)
        print(f"Total records found: {stats['total_records']}")
        print(f"Records processed: {stats['processed_records']}")
        print(f"Errors: {stats['errors']}")
        
        if stats['errors'] == 0:
            print("\n✅ Embedding generation completed successfully!")
        else:
            print(f"\n⚠️  Embedding generation completed with {stats['errors']} errors")
        
        # Verify results
        print("\nVerifying embeddings...")
        verification = verify_embeddings()
        print(f"Embedding coverage: {verification['embedding_percentage']:.1f}%")
        print(f"Average embedding dimension: {verification['avg_embedding_dimension']}")
        
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
