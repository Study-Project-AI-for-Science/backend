from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date
import re


class PaperMetadata(BaseModel):
    title: str = Field(min_length=3, max_length=300, description="Title of the paper")
    authors: List[str] = Field(min_length=1, description="List of author names")
    journal: Optional[str] = Field(max_length=200, description="Journal where the paper is published")
    field_of_study: Optional[str] = Field(None, max_length=200, description="Scientific field or subject area")
    publication_date: str = Field(description="Date of publication")
    doi: Optional[str] = Field(description="Digital Object Identifier DOI")
    keywords: List[str] = Field(min_length=3, description="List of keywords related to the paper")
