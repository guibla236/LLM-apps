from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any

class SearchType(str, Enum):
    """Available search types."""
    TICKETS_ONLY = "tickets_only"
    KB_ONLY = "kb_only"
    BOTH = "both"

class SearchResult(BaseModel):
    """Model for unified search results."""
    source: str = Field(..., description="Source of the result (ticket or kb)")
    id: str = Field(..., description="ID of the document/ticket")
    title: str = Field(..., description="Title or name of the document")
    content: str = Field(..., description="Relevant content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    score: float = Field(..., description="Relevance score")

class SearchRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=2000, description="Description of the support problem to search for")
    search_type: SearchType = Field(default=SearchType.BOTH, description="Search type: tickets_only, kb_only, both")
    hybrid_search: bool = Field(default=True, description="If True, performs hybrid search (Vector + BM25)")


class SearchMethod(str, Enum):
    VECTOR_ONLY = "vector_only"
    BM25_ONLY = "bm25_only"
    HYBRID = "hybrid"

class RawSearchRequest(BaseModel):
    query: str
    search_type: SearchType = SearchType.BOTH
    search_method: SearchMethod = SearchMethod.HYBRID
    k: int = 5