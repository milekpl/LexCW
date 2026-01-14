from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SearchFilter(BaseModel):
    field: str
    operator: str
    value: Any

class SortOrder(BaseModel):
    field: str
    direction: str = 'asc'

class SearchQuery(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    filters: List[SearchFilter] = Field(default_factory=list)
    sort_order: Optional[SortOrder] = None
    page: int = 1
    per_page: int = 20
