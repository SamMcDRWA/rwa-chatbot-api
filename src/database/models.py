"""
Database models for RWA Chatbot Phase 1
Defines the structure for storing Tableau object metadata and embeddings
"""

from sqlalchemy import Column, BigInteger, String, Text, ARRAY, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from .connection import Base


class TableauObject(Base):
    """
    Model for storing Tableau object metadata and embeddings
    Maps to the chatbot.objects table
    """
    __tablename__ = "objects"
    __table_args__ = {"schema": "chatbot"}
    
    # Primary key
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Tableau identifiers
    site_id = Column(String, nullable=False)
    object_type = Column(String, nullable=False)  # view | workbook | datasource
    object_id = Column(String, nullable=False)    # Tableau GUID
    
    # Object metadata
    title = Column(String, nullable=False)
    description = Column(Text)
    tags = Column(ARRAY(String))
    fields = Column(ARRAY(String))  # column/metric names
    project_name = Column(String)
    owner = Column(String)
    url = Column(Text)  # deep link
    
    # Search and embedding
    text_blob = Column(Text, nullable=False)  # concatenated text for search
    embedding = Column(Vector(384))  # vector embedding for semantic search
    
    # Timestamps
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<TableauObject(id={self.id}, type={self.object_type}, title='{self.title}')>"
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            'id': self.id,
            'site_id': self.site_id,
            'object_type': self.object_type,
            'object_id': self.object_id,
            'title': self.title,
            'description': self.description,
            'tags': self.tags,
            'fields': self.fields,
            'project_name': self.project_name,
            'owner': self.owner,
            'url': self.url,
            'text_blob': self.text_blob,
            'embedding': self.embedding.tolist() if self.embedding is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_tableau_data(cls, site_id: str, object_type: str, tableau_obj: dict, text_blob: str = None, embedding: list = None):
        """
        Create TableauObject instance from Tableau API data
        
        Args:
            site_id: Tableau site ID
            object_type: Type of object (view, workbook, datasource)
            tableau_obj: Dictionary from Tableau API
            text_blob: Concatenated text for search
            embedding: Vector embedding for semantic search
            
        Returns:
            TableauObject instance
        """
        # Extract common fields
        object_id = tableau_obj.get('id', '')
        title = tableau_obj.get('name', '')
        description = tableau_obj.get('description', '')
        project_name = tableau_obj.get('project', {}).get('name', '') if 'project' in tableau_obj else ''
        owner = tableau_obj.get('owner', {}).get('name', '') if 'owner' in tableau_obj else ''
        
        # Extract tags
        tags = []
        if 'tags' in tableau_obj and tableau_obj['tags']:
            tags = [tag.get('name', '') for tag in tableau_obj['tags'].get('tag', [])]
        
        # Extract fields (for views and datasources)
        fields = []
        if 'fields' in tableau_obj and tableau_obj['fields']:
            fields = [field.get('name', '') for field in tableau_obj['fields'].get('field', [])]
        
        # Build URL
        url = tableau_obj.get('webpageUrl', '')
        
        return cls(
            site_id=site_id,
            object_type=object_type,
            object_id=object_id,
            title=title,
            description=description,
            tags=tags,
            fields=fields,
            project_name=project_name,
            owner=owner,
            url=url,
            text_blob=text_blob or '',
            embedding=embedding
        )
