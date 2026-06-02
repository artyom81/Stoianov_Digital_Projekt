from __future__ import annotations
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

class Magazine(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    form: Optional[str] = None
    years: Optional[str] = None
    issues_count: Optional[int] = None
    issue_url: str
    collected_at: str  # ISO-String

class Issue(BaseModel):
    id: str                               # z.B. "06_2000-03-09" oder "06"
    magazine_id: int
    label: str                            # "06"
    date_human: Optional[str] = None
    date_iso: Optional[str] = None        # "YYYY-MM-DD"
    url: Optional[str] = None
    article_ids: List[int] = Field(default_factory=list)

class Article(BaseModel):
    id: int
    issue_id: str
    magazine_id: int
    title: str
    date_human: Optional[str] = None
    date_iso: Optional[str] = None
    source_url: str
    print_url: str
    pure_text_url: Optional[str] = None
    form: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    lead_image: Optional[str] = None
    bytes: Optional[int] = None
    sha1: Optional[str] = None
    status: Literal["ok", "missing", "failed"] = "ok"
    collected_at: str