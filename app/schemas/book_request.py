from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BookRequestCreate(BaseModel):
    book_id: int


class BookRequestResponse(BaseModel):
    request_id: int
    book_id: int
    user_id: int
    request_date: datetime
    status: str


    class Config:
        from_attributes = True


class BookRequestUpdate(BaseModel):
    status: Optional[str] = None