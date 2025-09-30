"""
Quality checks and guardrails for RWA Chatbot Phase 1
Ensures data quality and provides safety measures for indexing
"""

import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class QualityChecker:
    """Quality checker for Tableau indexing operations"""
    
    def __init__(self, site_id: str, site_name: str):
        self.site_id = site_id
        self.site_name = site_name
        self.quality_issues = []
        self.warnings = []
    
    def check_site_isolation(self, records: List[Dict[str, Any]]) -> bool:
        """
        Ensure all records have the correct site_id
        
        Args:
            records: List of records to check
            
        Returns:
            True if all records have correct site_id
        """
        issues = []
        
        for i, record in enumerate(records):
            record_site_id = record.get("site_id")
            if not record_site_id:
                issues.append(f"Record {i}: Missing site_id")
            elif record_site_id != self.site_id:
                issues.append(f"Record {i}: Incorrect site_id '{record_site_id}', expected '{self.site_id}'")
        
        if issues:
            self.quality_issues.extend(issues)
            logger.error(f"Site isolation issues found: {len(issues)} problems")
            return False
        
        logger.info(f"Site isolation check passed: {len(records)} records have correct site_id")
        return True
    
    def check_required_fields(self, records: List[Dict[str, Any]]) -> bool:
        """
        Check that all records have required fields
        
        Args:
            records: List of records to check
            
        Returns:
            True if all records have required fields
        """
        required_fields = ["object_id", "title", "object_type", "text_blob"]
        issues = []
        
        for i, record in enumerate(records):
            for field in required_fields:
                if not record.get(field):
                    issues.append(f"Record {i}: Missing required field '{field}'")
        
        if issues:
            self.quality_issues.extend(issues)
            logger.error(f"Required fields check failed: {len(issues)} problems")
            return False
        
        logger.info(f"Required fields check passed: {len(records)} records have all required fields")
        return True
    
    def check_description_quality(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Check description quality and provide statistics
        
        Args:
            records: List of records to check
            
        Returns:
            Dictionary with description quality statistics
        """
        stats = {
            "total_records": len(records),
            "with_descriptions": 0,
            "without_descriptions": 0,
            "empty_descriptions": 0,
            "short_descriptions": 0,
            "long_descriptions": 0
        }
        
        for record in records:
            description = record.get("description", "")
            
            if not description:
                stats["without_descriptions"] += 1
            elif description.strip() == "":
                stats["empty_descriptions"] += 1
            else:
                stats["with_descriptions"] += 1
                
                # Check description length
                if len(description) < 10:
                    stats["short_descriptions"] += 1
                elif len(description) > 500:
                    stats["long_descriptions"] += 1
        
        # Add warnings for poor description quality
        if stats["without_descriptions"] > stats["total_records"] * 0.5:
            self.warnings.append(f"High percentage of records without descriptions: {stats['without_descriptions']}/{stats['total_records']}")
        
        if stats["short_descriptions"] > stats["total_records"] * 0.3:
            self.warnings.append(f"Many records have very short descriptions: {stats['short_descriptions']}/{stats['total_records']}")
        
        logger.info(f"Description quality stats: {stats}")
        return stats
    
    def check_url_quality(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Check URL quality and deep link generation
        
        Args:
            records: List of records to check
            
        Returns:
            Dictionary with URL quality statistics
        """
        stats = {
            "total_records": len(records),
            "with_urls": 0,
            "without_urls": 0,
            "with_deep_links": 0,
            "without_deep_links": 0,
            "malformed_urls": 0
        }
        
        for record in records:
            url = record.get("url", "")
            deep_link = record.get("deep_link_url", "")
            
            if not url:
                stats["without_urls"] += 1
            else:
                stats["with_urls"] += 1
                
                # Check for malformed URLs
                if not url.startswith(("views/", "workbooks/", "datasources/")):
                    stats["malformed_urls"] += 1
            
            if deep_link:
                stats["with_deep_links"] += 1
            else:
                stats["without_deep_links"] += 1
        
        # Add warnings for URL issues
        if stats["malformed_urls"] > 0:
            self.warnings.append(f"Found {stats['malformed_urls']} malformed URLs")
        
        if stats["without_deep_links"] > stats["total_records"] * 0.1:
            self.warnings.append(f"Many records without deep links: {stats['without_deep_links']}/{stats['total_records']}")
        
        logger.info(f"URL quality stats: {stats}")
        return stats
    
    def check_text_blob_quality(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Check text blob quality for search indexing
        
        Args:
            records: List of records to check
            
        Returns:
            Dictionary with text blob quality statistics
        """
        stats = {
            "total_records": len(records),
            "empty_text_blobs": 0,
            "short_text_blobs": 0,
            "long_text_blobs": 0,
            "average_length": 0
        }
        
        total_length = 0
        
        for record in records:
            text_blob = record.get("text_blob", "")
            
            if not text_blob:
                stats["empty_text_blobs"] += 1
            else:
                length = len(text_blob)
                total_length += length
                
                if length < 20:
                    stats["short_text_blobs"] += 1
                elif length > 2000:
                    stats["long_text_blobs"] += 1
        
        if stats["total_records"] > 0:
            stats["average_length"] = total_length / stats["total_records"]
        
        # Add warnings for text blob issues
        if stats["empty_text_blobs"] > 0:
            self.warnings.append(f"Found {stats['empty_text_blobs']} records with empty text blobs")
        
        if stats["short_text_blobs"] > stats["total_records"] * 0.2:
            self.warnings.append(f"Many records have short text blobs: {stats['short_text_blobs']}/{stats['total_records']}")
        
        logger.info(f"Text blob quality stats: {stats}")
        return stats
    
    def run_all_checks(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run all quality checks on records
        
        Args:
            records: List of records to check
            
        Returns:
            Dictionary with all quality check results
        """
        logger.info(f"Running quality checks on {len(records)} records")
        
        results = {
            "site_isolation": self.check_site_isolation(records),
            "required_fields": self.check_required_fields(records),
            "description_quality": self.check_description_quality(records),
            "url_quality": self.check_url_quality(records),
            "text_blob_quality": self.check_text_blob_quality(records),
            "issues": self.quality_issues,
            "warnings": self.warnings
        }
        
        # Overall quality score
        critical_checks = [results["site_isolation"], results["required_fields"]]
        results["overall_quality"] = all(critical_checks)
        
        logger.info(f"Quality check completed. Overall quality: {results['overall_quality']}")
        logger.info(f"Issues: {len(self.quality_issues)}, Warnings: {len(self.warnings)}")
        
        return results


class RateLimiter:
    """Rate limiter for API calls with backoff and retry logic"""
    
    def __init__(self, max_requests_per_minute: int = 60, max_retries: int = 3):
        self.max_requests_per_minute = max_requests_per_minute
        self.max_retries = max_retries
        self.requests = []
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry logic"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def wait_if_needed(self):
        """Wait if we're approaching rate limits"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if req_time > minute_ago]
        
        # If we're at the limit, wait
        if len(self.requests) >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.requests[0]).total_seconds()
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.requests = []  # Clear after waiting
    
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a rate-limited request"""
        self.wait_if_needed()
        
        try:
            response = self.session.request(method, url, **kwargs)
            self.requests.append(datetime.now())
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise


class PaginationHelper:
    """Helper for paginating large result sets"""
    
    def __init__(self, page_size: int = 100, max_pages: int = None):
        self.page_size = page_size
        self.max_pages = max_pages
    
    def paginate_requests(self, fetch_func, *args, **kwargs) -> List[Any]:
        """
        Paginate through results using a fetch function
        
        Args:
            fetch_func: Function that accepts page parameter and returns results
            *args: Positional arguments for fetch_func
            **kwargs: Keyword arguments for fetch_func
            
        Returns:
            List of all results across all pages
        """
        all_results = []
        page = 1
        
        while True:
            try:
                logger.info(f"Fetching page {page} (page size: {self.page_size})")
                
                # Add page parameter to kwargs
                page_kwargs = kwargs.copy()
                page_kwargs["page"] = page
                page_kwargs["page_size"] = self.page_size
                
                results = fetch_func(*args, **page_kwargs)
                
                if not results:
                    logger.info(f"No more results on page {page}, stopping pagination")
                    break
                
                all_results.extend(results)
                logger.info(f"Page {page}: {len(results)} results, total: {len(all_results)}")
                
                # Check if we got fewer results than page size (last page)
                if len(results) < self.page_size:
                    logger.info("Last page reached (fewer results than page size)")
                    break
                
                # Check max pages limit
                if self.max_pages and page >= self.max_pages:
                    logger.info(f"Reached max pages limit: {self.max_pages}")
                    break
                
                page += 1
                
                # Small delay between pages
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
        
        logger.info(f"Pagination completed: {len(all_results)} total results across {page} pages")
        return all_results


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set
    
    Returns:
        True if environment is valid
    """
    # Check Tableau configuration
    tableau_vars = [
        'TABLEAU_SERVER_URL',
        'TABLEAU_PAT_NAME', 
        'TABLEAU_PAT_SECRET',
        'TABLEAU_SITE_NAME'
    ]
    
    missing_tableau = [var for var in tableau_vars if not os.getenv(var)]
    
    if missing_tableau:
        logger.error(f"Missing required Tableau environment variables: {missing_tableau}")
        return False
    
    # Check database configuration (support both DATABASE_URL and individual parameters)
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        logger.info("Using DATABASE_URL for database configuration")
        # Validate DATABASE_URL format
        if not database_url.startswith(('postgresql://', 'postgres://')):
            logger.error("DATABASE_URL must start with postgresql:// or postgres://")
            return False
    else:
        # Fallback to individual parameters
        db_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_db = [var for var in db_vars if not os.getenv(var)]
        
        if missing_db:
            logger.error(f"Missing required database environment variables: {missing_db}")
            logger.error("Either provide DATABASE_URL or individual DB_* parameters")
            return False
        
        logger.info("Using individual database parameters")
    
    # Check for placeholder values
    if os.getenv('TABLEAU_PAT_SECRET') == "***redacted***":
        logger.error("TABLEAU_PAT_SECRET is still set to placeholder value")
        return False
    
    # Check database password (only if using individual parameters)
    if not database_url and os.getenv('DB_PASSWORD') == "***redacted***":
        logger.error("DB_PASSWORD is still set to placeholder value")
        return False
    
    logger.info("Environment validation passed")
    return True


def get_indexing_recommendations(quality_results: Dict[str, Any]) -> List[str]:
    """
    Get recommendations based on quality check results
    
    Args:
        quality_results: Results from quality checks
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    # Description quality recommendations
    desc_stats = quality_results.get("description_quality", {})
    if desc_stats.get("without_descriptions", 0) > desc_stats.get("total_records", 1) * 0.3:
        recommendations.append("Consider asking authors to add descriptions to workbooks and views")
    
    # Text blob quality recommendations
    text_stats = quality_results.get("text_blob_quality", {})
    if text_stats.get("short_text_blobs", 0) > text_stats.get("total_records", 1) * 0.2:
        recommendations.append("Many records have short text blobs - consider improving metadata extraction")
    
    # URL quality recommendations
    url_stats = quality_results.get("url_quality", {})
    if url_stats.get("malformed_urls", 0) > 0:
        recommendations.append("Fix malformed URLs in Tableau metadata")
    
    # Overall recommendations
    if not quality_results.get("overall_quality", False):
        recommendations.append("Fix critical quality issues before proceeding with indexing")
    
    if len(quality_results.get("warnings", [])) > 5:
        recommendations.append("Address quality warnings to improve search results")
    
    return recommendations
