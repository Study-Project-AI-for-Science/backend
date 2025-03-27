from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date
import re


class PaperMetadata(BaseModel):
    title: str = Field(..., min_length=3, max_length=300, description="Title of the paper")
    authors: List[str] = Field(..., min_length=1, description="List of author names")
    journal: Optional[str] = Field(None, max_length=200, description="Journal where the paper is published")
    field_of_study: Optional[str] = Field(None, max_length=200, description="Scientific field or subject area")
    publication_date: date = Field(..., description="Date of publication")
    doi: Optional[str] = Field(None, description="Digital Object Identifier DOI")
    keywords: List[str] = Field(..., min_length=3, description="List of keywords related to the paper")

    @field_validator("doi")
    def validate_doi(cls, value):
        if value and not re.match(r"^10\.\d{4,9}/[\S]+$", value):
            raise ValueError("Invalid DOI format")
        return value

    @field_validator("authors", mode="before")
    def validate_author_names(cls, values):
        for value in values:
            if not re.match(r"^[A-Za-z ,.'-]+$", value):
                raise ValueError("Invalid author name format")
            if " " not in value:
                raise ValueError("must contain a space")
        return values

    @field_validator("publication_date", mode="before")
    def validate_publication_data(cls, value):
        if value and not re.match(
            r"\b(?:"
            r"(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}) |"  # DD-MM-YYYY, MM/DD/YYYY, etc.
            r"(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}) |"  # YYYY-MM-DD, YYYY/MM/DD
            r"(?:\d{1,2} \w{3,9} \d{2,4}) |"  # 01 Jan 2024, 1 January 2024
            r"(?:\w{3,9} \d{1,2},? \d{2,4})"  # January 1, 2024
            r")\b",
            value,
        ):
            raise ValueError("Invalid Publication Date Format")
        return value
