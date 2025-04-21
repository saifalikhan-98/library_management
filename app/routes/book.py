from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas.book import (
    BookCreate, BookUpdate, BookResponse, BookSearchParams,
    AuthorCreate, AuthorResponse, PublisherCreate, PublisherResponse,
    CategoryResponse
)
from app.schemas.paginated_response import PaginatedResponse
from app.schemas.user import UserToken
from app.security.access_level_middleware import require_role
from app.services.book_service import BookService
from app.services.book_lisiting_service import BookListingService

from app.utils.constants import ADMIN_ACCESS_LEVEL, LIBRARIAN_ACCESS_LEVEL, USER_ACCESS_LEVEL

router = APIRouter()

@router.post("/",response_model=BookResponse,status_code=201)
async def create_book(book: BookCreate,db: Session = Depends(get_db),
                      _:UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))):
    print(book)
    return BookService().add_book(db, book)


@router.get("/{book_id}",response_model=BookResponse)
async def get_book(
    book_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _:UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL, api_key_required=False))
):
    return BookService().get_book(db, book_id, pick_cache_if_available=True)


@router.put("/{book_id}",response_model=BookResponse)
async def update_book(
    book_data: BookUpdate,
    book_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _:UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    return BookService().edit_book(db, book_id, book_data)


@router.delete("/{book_id}",status_code=201)
async def delete_book(
    book_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _:UserToken = Depends(require_role(min_access_level=ADMIN_ACCESS_LEVEL))
):
    BookService().delete_book(db, book_id)
    return None


@router.get("/search-books/",response_model=PaginatedResponse)
async def search_books(
    query: str = Query(None, description="Search across title, ISBN, author, and publisher"),
    db: Session = Depends(get_db),

):
    search_params = BookSearchParams(
        query=query,
        category_id=1,
        available_only=False,
        sort_by='relevance',
        sort_order='desc'
    )
    return BookService().search_books(db, search_params, 1, 10)


@router.post(
    "/authors",
    response_model=AuthorResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_author(
    author: AuthorCreate,
    db: Session = Depends(get_db),
    _:UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    return BookService().add_author(db, author.name, author.biography)


@router.post(
    "/publishers",
    response_model=PublisherResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_publisher(
    publisher: PublisherCreate,
    db: Session = Depends(get_db),
    _:UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    return BookService().add_publisher(db, publisher.name, publisher.address, publisher.contact_info)



@router.post("/categories",response_model=CategoryResponse)
async def create_category(
    name: str,
    description: str = None,
    db: Session = Depends(get_db),
    _:UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))
):
    return BookService().add_category(db, name, description)




@router.get("/",response_model=PaginatedResponse[BookResponse])
async def list_books(
        title: Optional[str] = Query(None, description="Filter by title"),
        author_id: Optional[int] = Query(None, description="Filter by author ID"),
        publisher_id: Optional[int] = Query(None, description="Filter by publisher ID"),
        category_id: Optional[int] = Query(None, description="Filter by category ID"),
        year_from: Optional[int] = Query(None, description="Filter by publication year (from)"),
        year_to: Optional[int] = Query(None, description="Filter by publication year (to)"),
        available_only: bool = Query(False, description="Show only available books"),
        sort_by: str = Query("title", description="Sort by field: title, author, publisher, year, added_date"),
        sort_order: str = Query("asc", description="Sort order: asc or desc"),
        page: int = Query(1, ge=1, description="Page number"),
        items_per_page: int = Query(10, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db),
        _:UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL, api_key_required=False))
):
    return BookListingService().list_books(
        db=db,
        title=title,
        author_id=author_id,
        publisher_id=publisher_id,
        category_id=category_id,
        year_from=year_from,
        year_to=year_to,
        available_only=available_only,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        items_per_page=items_per_page
    )


@router.get("/authors/list",response_model=PaginatedResponse[AuthorResponse])
async def list_authors(name: Optional[str] = Query(None, description="Filter by author name"),
                       sort_by: str = Query("name", description="Sort by field: name, book_count"),
                       sort_order: str = Query("asc", description="Sort order: asc or desc"),
                       page: int = Query(1, ge=1, description="Page number"),
                       items_per_page: int = Query(10, ge=1, le=100, description="Items per page"),
                       db: Session = Depends(get_db),
                       _:UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL, api_key_required=False))
                       ):
    return BookListingService().list_authors(
        db=db,
        name=name,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        items_per_page=items_per_page
    )


@router.get("/publishers/list",response_model=PaginatedResponse[PublisherResponse])
async def list_publishers(name: Optional[str] = Query(None, description="Filter by publisher name"),
                          sort_by: str = Query("name", description="Sort by field: name, book_count"),
                          sort_order: str = Query("asc", description="Sort order: asc or desc"),
                          page: int = Query(1, ge=1, description="Page number"),
                          items_per_page: int = Query(10, ge=1, le=100, description="Items per page"),
                          db: Session = Depends(get_db),
                          _: UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL, api_key_required=False))
                         ):
    return BookListingService().list_publishers(
        db=db,
        name=name,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        items_per_page=items_per_page
    )


@router.get("/categories/list",response_model=PaginatedResponse[CategoryResponse])
async def list_categories(name: Optional[str] = Query(None, description="Filter by category name"),
                          sort_by: str = Query("name", description="Sort by field: name, book_count"),
                          sort_order: str = Query("asc", description="Sort order: asc or desc"),
                          page: int = Query(1, ge=1, description="Page number"),
                          items_per_page: int = Query(10, ge=1, le=100, description="Items per page"),
                          db: Session = Depends(get_db),
                          _: UserToken = Depends(require_role(min_access_level=USER_ACCESS_LEVEL, api_key_required=False))
                          ):
    return BookListingService().list_categories(
        db=db,
        name=name,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        items_per_page=items_per_page
    )