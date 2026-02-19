"""SQLModel models for Concept Runner."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Concept(SQLModel, table=True):
    __tablename__ = "concepts"

    id: Optional[int] = Field(default=None, primary_key=True)
    idea: str
    slug: str = Field(unique=True)
    source: str = Field(default="pubmed")  # pubmed, web, both
    status: str = Field(default="created")  # created, searching, retrieving, analyzing, reflecting, gap_filling, writing, generating_cover, published, failed
    progress: int = Field(default=0)
    gap_iteration: int = Field(default=0)

    # Pipeline data (JSON text)
    search_queries: Optional[str] = None  # JSON list of query strings
    found_papers: Optional[str] = None  # JSON list of paper dicts
    paper_analyses: Optional[str] = None  # JSON list of analysis dicts
    knowledge_gaps: Optional[str] = None  # JSON list of gap strings
    sources: Optional[str] = None  # JSON list of source dicts

    # Output
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None  # Final markdown article
    cover_image_path: Optional[str] = None

    error_message: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class Paper(SQLModel, table=True):
    __tablename__ = "papers"

    pmid: str = Field(primary_key=True)
    pmc_id: Optional[str] = None
    title: str = ""
    abstract: Optional[str] = None
    authors: Optional[str] = None  # JSON list
    journal: Optional[str] = None
    year: Optional[str] = None
    doi: Optional[str] = None
    fulltext: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebSource(SQLModel, table=True):
    __tablename__ = "web_sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True)
    title: str = ""
    snippet: Optional[str] = None  # Search result snippet
    fulltext: Optional[str] = None  # Tavily extract raw_content
    domain: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
