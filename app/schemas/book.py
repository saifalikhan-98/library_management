from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from fastapi import HTTPException


class AuthorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    biography: Optional[str] = None


class AuthorCreate(AuthorBase):
    pass


class AuthorResponse(AuthorBase):
    author_id: int

    model_config = ConfigDict(from_attributes=True)


class PublisherBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    address: Optional[str] = None
    contact_info: Optional[str] = None


class PublisherCreate(PublisherBase):
    pass


class PublisherResponse(PublisherBase):
    publisher_id: int

    model_config = ConfigDict(from_attributes=True)


class BookAuthorBase(BaseModel):
    author_id: int



class BookAuthorCreate(BookAuthorBase):
    pass


class BookAuthorResponse(BookAuthorBase):
    author: Optional[AuthorResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(BaseModel):
    category_id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BookBase(BaseModel):
    isbn: str = Field(..., min_length=10, max_length=20)
    title: str = Field(..., min_length=1, max_length=255)
    publisher_id: Optional[int] = None
    publication_year: Optional[int] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    total_copies: int = Field(1, ge=1)

    @field_validator('publication_year')
    @classmethod
    def year_must_be_valid(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v < 1900 or v > current_year:
                raise HTTPException(status_code=400, detail=f'Publication year must be between 1900 and {current_year}')
        return v

    @field_validator('isbn')
    @classmethod
    def validate_isbn(cls, v):
        if v is None:
            return v
        if len(v) < 10:
            raise HTTPException(status_code=400, detail='ISBN must be atleast 10 digits')
        return v


class BookCreate(BookBase):
    authors: List[BookAuthorCreate]


class BookUpdate(BaseModel):
    isbn: Optional[str] = Field(None, min_length=10, max_length=20)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    publisher_id: Optional[int] = None
    publication_year: Optional[int] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    total_copies: Optional[int] = Field(None, ge=1)
    authors: Optional[List[BookAuthorCreate]] = None

    @field_validator('publication_year')
    @classmethod
    def year_must_be_valid(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v < 1900 or v > current_year:
                raise HTTPException(status_code=400, detail=f'Publication year must be between 1900 and {current_year}')
        return v

    @field_validator('isbn')
    @classmethod
    def validate_isbn(cls, v):
        if v is None:
            return v
        if len(v)<10:
            raise HTTPException(status_code=400, detail='ISBN must be atleast 10 digits')
        return v


class BookInDB(BookBase):
    book_id: int
    available_copies: int
    added_date: datetime
    category: Optional[CategoryResponse] = None
    publisher: Optional[PublisherResponse] = None
    authors: List[BookAuthorResponse] = []

    model_config = ConfigDict(from_attributes=True)


class BookResponse(BookInDB):
    pass

    class Config:
        from_attributes=True


class BookSearchParams(BaseModel):
    query: Optional[str] = None
    category_id: Optional[int] = None
    available_only: bool = False
    sort_by: Optional[str] = "relevance"
    sort_order: Optional[str] = "desc"