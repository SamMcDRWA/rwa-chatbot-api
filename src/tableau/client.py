"""
Tableau REST API Client for RWA Chatbot Phase 1
Handles authentication and object listing from Tableau Server
"""

import requests
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TableauClient:
    """Tableau REST API client for authentication and data retrieval"""
    
    def __init__(self, server_url: str, pat_name: str, pat_secret: str, site_name: str):
        self.server = server_url.rstrip('/')
        self.pat_name = pat_name
        self.pat_secret = pat_secret
        self.site_name = site_name
        self.token = None
        self.site_id = None
        self.session = requests.Session()
    
    def _parse_xml_response(self, response):
        """Parse XML response from Tableau API"""
        try:
            root = ET.fromstring(response.content)
            
            # Check for errors (handle namespaces)
            error = root.find('.//{http://tableau.com/api}error')
            if error is None:
                # Try without namespace as fallback
                error = root.find('.//error')
            
            if error is not None:
                error_code = error.get('code', 'Unknown')
                error_summary = error.find('{http://tableau.com/api}summary')
                if error_summary is None:
                    error_summary = error.find('summary')
                error_msg = error_summary.text if error_summary is not None else 'Unknown error'
                raise Exception(f"Tableau API error: {error_code} - {error_msg}")
            
            return root
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML response: {e}")
            logger.error(f"Response content: {response.text[:500]}...")
            raise
    
    def _xml_to_dict(self, element):
        """Convert XML element to dictionary"""
        result = {}
        
        # Add attributes
        if element.attrib:
            result.update(element.attrib)
        
        # Add text content if no children
        if len(element) == 0 and element.text:
            return element.text.strip()
        
        # Process children
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
        
    def signin(self) -> bool:
        """
        Authenticate with Tableau Server using Personal Access Token
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            url = f"{self.server}/api/3.20/auth/signin"
            payload = {
                "credentials": {
                    "personalAccessTokenName": self.pat_name,
                    "personalAccessTokenSecret": self.pat_secret,
                    "site": {"contentUrl": self.site_name}
                }
            }
            
            logger.info(f"Signing in to Tableau Server: {self.server}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            # Parse XML response
            root = self._parse_xml_response(response)
            
            # Extract credentials (handle namespaces)
            credentials = root.find('.//{http://tableau.com/api}credentials')
            if credentials is None:
                # Try without namespace as fallback
                credentials = root.find('.//credentials')
                if credentials is None:
                    logger.error("No credentials found in response")
                    return False
            
            # Get token from attribute
            self.token = credentials.get('token')
            if not self.token:
                logger.error("No token found in credentials")
                return False
            
            # Get site ID from site element
            site_elem = credentials.find('{http://tableau.com/api}site')
            if site_elem is None:
                # Try without namespace as fallback
                site_elem = credentials.find('site')
                if site_elem is None:
                    logger.error("No site element found in credentials")
                    return False
            
            self.site_id = site_elem.get('id')
            if not self.site_id:
                logger.error("No site ID found in site element")
                return False
            
            logger.info(f"Successfully signed in. Site ID: {self.site_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to sign in to Tableau Server: {e}")
            return False
        except KeyError as e:
            logger.error(f"Unexpected response format from Tableau Server: {e}")
            return False
    
    def _headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        if not self.token:
            raise ValueError("Not authenticated. Call signin() first.")
        return {"X-Tableau-Auth": self.token}
    
    def list_workbooks(self, project_filter: Optional[List[str]] = None) -> List[dict]:
        """
        List all workbooks in the site
        
        Args:
            project_filter: Optional list of project names to filter by
            
        Returns:
            List of workbook dictionaries
        """
        if not self.token:
            raise ValueError("Not authenticated. Call signin() first.")
            
        items = []
        page = 1
        
        try:
            while True:
                # Build URL with optional project filter
                url = f"{self.server}/api/3.20/sites/{self.site_id}/workbooks"
                params = {
                    "pageSize": 100,
                    "pageNumber": page
                }
                
                if project_filter:
                    # Add project filter if specified
                    project_filter_str = ",".join(project_filter)
                    params["filter"] = f"projectName:in:[{project_filter_str}]"
                
                response = self.session.get(url, headers=self._headers(), params=params)
                response.raise_for_status()
                
                # Parse XML response
                root = self._parse_xml_response(response)
                workbooks_elem = root.find('.//{http://tableau.com/api}workbooks')
                
                if workbooks_elem is not None:
                    workbook_list = workbooks_elem.findall('{http://tableau.com/api}workbook')
                    workbooks = [self._xml_to_dict(wb) for wb in workbook_list]
                    items.extend(workbooks)
                else:
                    workbooks = []
                
                logger.info(f"Retrieved {len(workbooks)} workbooks from page {page}")
                
                if len(workbooks) < 100:
                    break
                page += 1
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list workbooks: {e}")
            raise
            
        logger.info(f"Total workbooks retrieved: {len(items)}")
        return items
    
    def list_views(self, project_filter: Optional[List[str]] = None) -> List[dict]:
        """
        List all views in the site
        
        Args:
            project_filter: Optional list of project names to filter by
            
        Returns:
            List of view dictionaries
        """
        if not self.token:
            raise ValueError("Not authenticated. Call signin() first.")
            
        items = []
        page = 1
        
        try:
            while True:
                # Build URL with optional project filter
                url = f"{self.server}/api/3.20/sites/{self.site_id}/views"
                params = {
                    "pageSize": 100,
                    "pageNumber": page
                }
                
                if project_filter:
                    # Add project filter if specified
                    project_filter_str = ",".join(project_filter)
                    params["filter"] = f"projectName:in:[{project_filter_str}]"
                
                response = self.session.get(url, headers=self._headers(), params=params)
                response.raise_for_status()
                
                # Parse XML response
                root = self._parse_xml_response(response)
                views_elem = root.find('.//{http://tableau.com/api}views')
                
                if views_elem is not None:
                    view_list = views_elem.findall('{http://tableau.com/api}view')
                    views = [self._xml_to_dict(view) for view in view_list]
                    items.extend(views)
                else:
                    views = []
                
                logger.info(f"Retrieved {len(views)} views from page {page}")
                
                if len(views) < 100:
                    break
                page += 1
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list views: {e}")
            raise
            
        logger.info(f"Total views retrieved: {len(items)}")
        return items
    
    def list_views_for_workbook(self, workbook_id: str) -> List[dict]:
        """
        List all views for a specific workbook
        
        Args:
            workbook_id: The Tableau workbook ID
            
        Returns:
            List of view dictionaries
        """
        if not self.token:
            raise ValueError("Not authenticated. Call signin() first.")
            
        try:
            url = f"{self.server}/api/3.20/sites/{self.site_id}/workbooks/{workbook_id}/views"
            params = {"includeUsageStatistics": "false"}
            
            response = self.session.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            
            # Parse XML response
            root = self._parse_xml_response(response)
            views_elem = root.find('.//{http://tableau.com/api}views')
            
            if views_elem is not None:
                view_list = views_elem.findall('{http://tableau.com/api}view')
                views = [self._xml_to_dict(view) for view in view_list]
            else:
                views = []
                
            logger.info(f"Retrieved {len(views)} views for workbook {workbook_id}")
            return views
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list views for workbook {workbook_id}: {e}")
            raise
    
    def list_datasources(self, project_filter: Optional[List[str]] = None) -> List[dict]:
        """
        List all datasources in the site
        
        Args:
            project_filter: Optional list of project names to filter by
            
        Returns:
            List of datasource dictionaries
        """
        if not self.token:
            raise ValueError("Not authenticated. Call signin() first.")
            
        items = []
        page = 1
        
        try:
            while True:
                url = f"{self.server}/api/3.20/sites/{self.site_id}/datasources"
                params = {
                    "pageSize": 100,
                    "pageNumber": page
                }
                
                if project_filter:
                    project_filter_str = ",".join(project_filter)
                    params["filter"] = f"projectName:in:[{project_filter_str}]"
                
                response = self.session.get(url, headers=self._headers(), params=params)
                response.raise_for_status()
                
                # Parse XML response
                root = self._parse_xml_response(response)
                datasources_elem = root.find('.//{http://tableau.com/api}datasources')
                
                if datasources_elem is not None:
                    datasource_list = datasources_elem.findall('{http://tableau.com/api}datasource')
                    datasources = [self._xml_to_dict(ds) for ds in datasource_list]
                    items.extend(datasources)
                else:
                    datasources = []
                
                logger.info(f"Retrieved {len(datasources)} datasources from page {page}")
                
                if len(datasources) < 100:
                    break
                page += 1
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list datasources: {e}")
            raise
            
        logger.info(f"Total datasources retrieved: {len(items)}")
        return items
    
    def get_workbook_details(self, workbook_id: str) -> dict:
        """
        Get detailed information about a specific workbook
        
        Args:
            workbook_id: The Tableau workbook ID
            
        Returns:
            Workbook details dictionary
        """
        if not self.token:
            raise ValueError("Not authenticated. Call signin() first.")
            
        try:
            url = f"{self.server}/api/3.20/sites/{self.site_id}/workbooks/{workbook_id}"
            params = {}
            
            response = self.session.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            
            # Parse XML response
            root = self._parse_xml_response(response)
            workbook_elem = root.find('.//workbook')
            
            if workbook_elem is not None:
                workbook = self._xml_to_dict(workbook_elem)
            else:
                workbook = {}
                
            logger.info(f"Retrieved details for workbook {workbook_id}")
            return workbook
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get workbook details for {workbook_id}: {e}")
            raise
    
    def list_projects(self) -> List[dict]:
        """
        List all projects in the site
        
        Returns:
            List of project dictionaries with id, name, description, etc.
        """
        if not self.token:
            raise ValueError("Not authenticated. Call signin() first.")
        
        try:
            url = f"{self.server}/api/3.20/sites/{self.site_id}/projects"
            response = self.session.get(url, headers=self._headers())
            response.raise_for_status()
            
            root = self._parse_xml_response(response)
            projects = []
            
            # Find all project elements
            for project_elem in root.findall('.//{http://tableau.com/api}project'):
                project = {
                    'id': project_elem.get('id'),
                    'name': project_elem.get('name'),
                    'description': project_elem.get('description', ''),
                    'created_at': project_elem.get('createdAt', ''),
                    'updated_at': project_elem.get('updatedAt', ''),
                    'content_permissions': project_elem.get('contentPermissions', ''),
                }
                projects.append(project)
            
            logger.info(f"Retrieved {len(projects)} projects from Tableau")
            return projects
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list projects: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing projects response: {e}")
            return []
    
    def list_workbooks_by_project(self, project_id: str) -> List[dict]:
        """
        List workbooks for a specific project
        
        Args:
            project_id: The project ID to get workbooks for
            
        Returns:
            List of workbook dictionaries
        """
        if not self.token:
            raise ValueError("Not authenticated. Call signin() first.")
        
        try:
            url = f"{self.server}/api/3.20/sites/{self.site_id}/projects/{project_id}/workbooks"
            response = self.session.get(url, headers=self._headers())
            response.raise_for_status()
            
            root = self._parse_xml_response(response)
            workbooks = []
            
            # Find all workbook elements
            for workbook_elem in root.findall('.//{http://tableau.com/api}workbook'):
                workbook = {
                    'id': workbook_elem.get('id'),
                    'name': workbook_elem.get('name'),
                    'description': workbook_elem.get('description', ''),
                    'created_at': workbook_elem.get('createdAt', ''),
                    'updated_at': workbook_elem.get('updatedAt', ''),
                    'project_id': project_id,
                }
                workbooks.append(workbook)
            
            logger.info(f"Retrieved {len(workbooks)} workbooks for project {project_id}")
            return workbooks
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list workbooks for project {project_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing workbooks response for project {project_id}: {e}")
            return []

    def signout(self) -> bool:
        """
        Sign out from Tableau Server
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.token:
            logger.warning("Not signed in, nothing to sign out")
            return True
            
        try:
            url = f"{self.server}/api/3.20/auth/signout"
            response = self.session.post(url, headers=self._headers())
            response.raise_for_status()
            
            self.token = None
            self.site_id = None
            logger.info("Successfully signed out from Tableau Server")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to sign out: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        if not self.signin():
            raise ConnectionError("Failed to authenticate with Tableau Server")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.signout()
