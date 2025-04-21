from fastapi import HTTPException, status
from sqlalchemy import case, text
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from sqlalchemy.sql import func, or_, desc

from app.core.redis_cache_service import RedisCacheService
from app.models import Category
from app.models.book import Book, Author, Publisher, BookAuthor
from app.schemas.book import BookCreate, BookUpdate, BookResponse, BookSearchParams
from app.schemas.paginated_response import PaginatedResponse, paginate_query


class BookService:

    def __init__(self):
        self.cache_service = RedisCacheService(default_ttl=3600)

    def add_book(self, db: Session, book: BookCreate) -> Book:
        existing_book = db.query(Book).filter(Book.isbn == book.isbn).first()
        if existing_book:
            raise HTTPException(
                status_code=400,
                detail=f"Book with ISBN {book.isbn} already exists"
            )

        db_book = Book(
            isbn=book.isbn,
            title=book.title,
            publisher_id=book.publisher_id,
            publication_year=book.publication_year,
            category_id=book.category_id,
            description=book.description,
            total_copies=book.total_copies,
            available_copies=book.total_copies
        )

        db.add(db_book)
        db.flush()

        for author in book.authors:
            db_book_author = BookAuthor(
                book_id=db_book.book_id,
                author_id=author.author_id,
            )
            db.add(db_book_author)

        db.commit()
        db.refresh(db_book)
        return db_book

    def get_book(self, db: Session, book_id: int, pick_cache_if_available=False) -> Book:
        cache_key = f"book_id_:{book_id}"

        cached_result = self.cache_service.get(cache_key)
        if pick_cache_if_available and cached_result is not None:
            return cached_result
        book = db.query(Book).options(
            joinedload(Book.category),
            joinedload(Book.publisher),
            joinedload(Book.authors).joinedload(BookAuthor.author)
        ).filter(Book.book_id == book_id).first()

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )

        self.cache_service.set(
            cache_key,
            BookResponse.model_validate(book).model_dump(mode='json')
        )
        return book

    def edit_book(self, db: Session, book_id: int, book_data: BookUpdate) -> Book:
        db_book = self.get_book(db, book_id)

        if book_data.isbn and book_data.isbn != db_book.isbn:
            existing_book = db.query(Book).filter(Book.isbn == book_data.isbn).first()
            if existing_book:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Book with ISBN {book_data.isbn} already exists"
                )

        update_data = book_data.model_dump(exclude_unset=True)
        if "authors" in update_data:
            authors = update_data.pop("authors")

            db.query(BookAuthor).filter(BookAuthor.book_id == book_id).delete()

            for author in authors:
                db_book_author = BookAuthor(
                    book_id=book_id,
                    author_id=author["author_id"],
                )
                db.add(db_book_author)

        for key, value in update_data.items():
            setattr(db_book, key, value)

        if 'total_copies' in update_data:
            borrowed_copies = db_book.total_copies - db_book.available_copies
            new_available = max(0, db_book.total_copies - borrowed_copies)
            db_book.available_copies = new_available

        db.commit()
        db.refresh(db_book)
        return db_book

    def delete_book(self, db: Session, book_id: int) -> None:
        db_book = self.get_book(db, book_id)

        active_borrowings = db.query(Book).join(
            Book.borrowings
        ).filter(
            Book.book_id == book_id,
            Book.borrowings.any(is_returned=False)
        ).first()

        if active_borrowings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a book that has active borrowings"
            )

        db.delete(db_book)
        db.commit()

    def search_books(self, db: Session, search_params: BookSearchParams, page: int = 1,
                     items_per_page: int = 10) -> PaginatedResponse:



        cache_key = f"book_search:{search_params.query.lower()}:{page}:{items_per_page}"

        cached_result = self.cache_service.get(cache_key)
        if cached_result:
            return PaginatedResponse(**cached_result)

        query = db.query(Book).options(
            joinedload(Book.category),
            joinedload(Book.publisher),
            joinedload(Book.authors).joinedload(BookAuthor.author)
        )

        if search_params.query and search_params.query.strip():
            search_term = search_params.query.strip().lower()
            startswith_books = db.query(Book.book_id).filter(
                func.lower(Book.title).like(f"{search_term}%")
            ).subquery()


            startswith_query = query.filter(Book.book_id.in_(startswith_books))
            startswith_query = startswith_query.order_by(Book.title)
            startswith_count = startswith_query.count()
            total_count = startswith_count


            if startswith_count >= page * items_per_page:
                offset = (page - 1) * items_per_page
                books = startswith_query.offset(offset).limit(items_per_page).all()
            else:
                startswith_offset = (page - 1) * items_per_page
                startswith_limit = startswith_count - startswith_offset
                startswith_books = startswith_query.offset(startswith_offset).limit(startswith_limit).all()

                books = startswith_books

        else:
            if search_params.category_id:
                query = query.filter(Book.category_id == search_params.category_id)

            if search_params.available_only:
                query = query.filter(Book.available_copies > 0)

            query = query.order_by(Book.title)
            total_count = query.count()


            offset = (page - 1) * items_per_page
            books = query.offset(offset).limit(items_per_page).all()

        # Create response objects
        book_responses = [BookResponse.model_validate(book) for book in books]

        skip = (page - 1) * items_per_page
        limit = items_per_page
        has_more = (skip + limit) < total_count

        # Calculate total pages
        total_pages = (total_count + items_per_page - 1) // items_per_page

        # Create paginated response
        response = PaginatedResponse(
            data=book_responses,
            total=total_count,
            skip=skip,
            limit=limit,
            has_more=has_more
        )

        # Cache the result
        self.cache_service.set(
            cache_key,
            {
                "items": [book.model_dump() for book in book_responses],
                "total": total_count,
                "page": page,
                "items_per_page": items_per_page,
                "pages": total_pages
            }
        )

        return response

    def add_author(self, db: Session, name: str, biography: Optional[str] = None) -> Author:
        existing_author = db.query(Author).filter(Author.name == name).first()
        if existing_author:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Author with name '{name}' already exists"
            )

        db_author = Author(name=name, biography=biography)
        db.add(db_author)
        db.commit()
        db.refresh(db_author)
        return db_author



    def add_publisher(self, db: Session, name: str, address: Optional[str] = None,
                      contact_info: Optional[str] = None) -> Publisher:
        existing_publisher = db.query(Publisher).filter(Publisher.name == name).first()
        if existing_publisher:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Publisher with name '{name}' already exists"
            )

        db_publisher = Publisher(name=name, address=address, contact_info=contact_info)
        db.add(db_publisher)
        db.commit()
        db.refresh(db_publisher)
        return db_publisher



    def add_category(self, db: Session, name: str, description: Optional[str] = None) -> Category:
        existing_category = db.query(Category).filter(Category.name == name).first()
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with name '{name}' already exists"
            )

        db_category = Category(name=name, description=description)
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category