"""Catalog database models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from .catalog_base import CatalogBase


class CatalogProject(CatalogBase):
    """Metadata for a project entry."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    db_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_opened = Column(DateTime, nullable=True)
