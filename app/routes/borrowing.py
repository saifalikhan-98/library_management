from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.borrowing import (
    BorrowingCreate, BorrowingResponse, BorrowingHistory, BorrowingWithBookInfo
)
from app.schemas.generic import GenericResponse
from app.schemas.paginated_response import PaginatedResponse
from app.schemas.user import UserToken
from app.security.access_level_middleware import require_role
from app.services.borrowing_service import BorrowingService

from app.utils.constants import LIBRARIAN_ACCESS_LEVEL, USER_ACCESS_LEVEL, BorrowingStatus

router = APIRouter()


@router.post("/",response_model=BorrowingResponse,status_code=status.HTTP_201_CREATED)
async def borrow_book(
        borrowing_data: BorrowingCreate,
        db: Session = Depends(get_db),
        current_user: UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL,api_key_required=True))
):
    return BorrowingService().borrow_book(
        db=db,
        user_id=current_user.user_id,
        borrowing_data=borrowing_data
    )


@router.put("/{borrowing_id}/return",response_model=BorrowingResponse)
async def return_book(
        borrowing_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        _:UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL,api_key_required=True))
):
    return BorrowingService().return_book(
        db=db,
        borrowing_id=borrowing_id
    )


@router.get("/{borrowing_id}",response_model=BorrowingResponse)
async def get_borrowing(
        borrowing_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        _: UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL,api_key_required=True))
):
    borrowing = BorrowingService().get_borrowing(db, borrowing_id)
    return borrowing


@router.get("/users/me/borrowings", response_model=BorrowingHistory)
async def get_my_borrowings(
        db: Session = Depends(get_db),
        current_user: UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL ,api_key_required=True))
):
    return BorrowingService().get_user_borrowings(
        db=db,
        user_id=current_user.user_id
    )


@router.get("/users/{user_id}/borrowings",response_model=BorrowingHistory)
async def get_user_borrowings(
        user_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        _:UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    return BorrowingService().get_user_borrowings(
        db=db,
        user_id=user_id
    )


@router.post("/update-overdue",response_model=GenericResponse,status_code=status.HTTP_200_OK)
async def update_overdue_status(
    db: Session = Depends(get_db),
    _: UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    count = BorrowingService().update_overdue_status(db)
    return GenericResponse(**{"message": f"Updated {count} borrowings to overdue status"})

@router.get("/books/overdue",response_model=List[BorrowingWithBookInfo])
async def get_overdue_borrowings(
        db: Session = Depends(get_db),
        _: UserToken= Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    print("here")
    return BorrowingService().get_overdue_borrowings(db)


@router.get("/books/{book_id}/borrowings",response_model=List[BorrowingWithBookInfo])
async def get_book_borrowing_history(
        book_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        _: UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    return BorrowingService().get_book_borrowing_history(
        db=db,
        book_id=book_id
    )


@router.get("/",response_model=PaginatedResponse[BorrowingWithBookInfo])
async def list_borrowings(
        user_id: Optional[int] = Query(None, description="Filter by user ID"),
        book_id: Optional[int] = Query(None, description="Filter by book ID"),
        status: Optional[BorrowingStatus] = Query(None, description="Filter by return status"),
        overdue_only: bool = Query(False, description="Show only overdue borrowings"),
        sort_by: str = Query("borrow_date", description="Sort by: borrow_date, due_date, return_date"),
        sort_order: str = Query("desc", description="Sort order: asc or desc"),
        page: int = Query(1, ge=1, description="Page number"),
        items_per_page: int = Query(10, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db),
        _:UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    return BorrowingService().list_borrowings(
        db=db,
        user_id=user_id,
        book_id=book_id,
        status=status,
        overdue_only=overdue_only,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        items_per_page=items_per_page
    )

