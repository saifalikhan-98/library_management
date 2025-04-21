from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from app.schemas.book import BookResponse
from app.utils.constants import BorrowingStatus


class BorrowingBase(BaseModel):
    book_id: int
    due_date: datetime



class BorrowingCreate(BaseModel):
    book_id: int


class BorrowingUpdate(BaseModel):
    status: Optional[BorrowingStatus] = None
    due_date: Optional[datetime] = None



class BorrowingReturn(BaseModel):
    status: BorrowingStatus



class BorrowingInDB(BorrowingBase):
    borrowing_id: int
    user_id: int
    borrow_date: datetime
    return_date: Optional[datetime] = None
    status: BorrowingStatus

    model_config = ConfigDict(from_attributes=True)


class BorrowingWithBookInfo(BorrowingInDB):
    book_title: str
    book_authors: str
    book_isbn: str

    model_config = ConfigDict(from_attributes=True)


class BorrowingResponse(BorrowingInDB):
    book: Optional[BookResponse] = None

    model_config = ConfigDict(from_attributes=True)


class BorrowingHistory(BaseModel):
    current_borrowings: List[BorrowingWithBookInfo]
    past_borrowings: List[BorrowingWithBookInfo]
