from pydantic import BaseModel, Field, AnyUrl
from typing import List, Optional

class MagazineMeta(BaseModel):
    magazine_id: int
    magazine_name: str
    city: Optional[str] = None
    country: Optional[str] = None
    form: Optional[str] = None
    years: Optional[str] = None
    issues_count: Optional[int] = None
    language: str = "ru"
    rights: Optional[str] = None
    license_note: Optional[str] = None

class IssueMeta(BaseModel):
    issue_label: str = Field(..., pattern=r"^\d{2}$")
    issue_date_human: Optional[str] = None
    issue_date_iso: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    articles_count: int

class ArticleListEntry(BaseModel):
    order: int
    article_id: int
    title_link: str
    article_url: AnyUrl
    print_url: AnyUrl

class Listing(BaseModel):
    issue: IssueMeta
    articles: List[ArticleListEntry]

class ArticleMeta(BaseModel):
    magazine_id: int
    magazine_name: str
    issue_label: str
    issue_date_iso: str
    order: int
    article_id: int
    title_link: str
    title_h1: Optional[str] = None
    article_url: AnyUrl
    print_url: AnyUrl
    fetched_at: Optional[str] = None