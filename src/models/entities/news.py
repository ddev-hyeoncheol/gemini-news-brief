from datetime import datetime

from typing import Any
from pydantic import BaseModel, Field


class BronzeNewsModel(BaseModel):
    news_id: str = Field(..., description="뉴스 ID(Hash)")
    source: str = Field(..., description="출처")
    title: str = Field(..., description="제목")
    url: str = Field(..., description="뉴스 URL")
    image_url: str | None = Field(default=None, description="이미지 URL")
    thumbnail_url: str | None = Field(default=None, description="썸네일 URL")
    content: str | None = Field(default=None, description="본문")
    category: str | None = Field(default=None, description="카테고리")
    author: str | None = Field(default=None, description="작성자")
    published_at: datetime | None = Field(default=None, description="발행일시")
    updated_at: datetime | None = Field(default=None, description="수정일시")
    collected_at: datetime = Field(..., description="수집일시")
    metadata: dict[str, Any] | None = Field(default=None, description="추가 메타데이터")
