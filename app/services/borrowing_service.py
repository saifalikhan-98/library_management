from dns.e164 import query
from fastapi import HTTPException, status,BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, and_, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.redis_cache_service import RedisCacheService
from app.models import Borrowing
from app.models.book import Book, BookAuthor, Author
from app.models.books_queue import BookRequestQueue
from app.schemas.book_request import BookRequestResponse
from app.schemas.borrowing import BorrowingCreate, BorrowingWithBookInfo, BorrowingHistory, BorrowingUpdate
from app.schemas.paginated_response import PaginatedResponse
from app.services.book_service import BookService
from app.services.notification_service import NotificationService
from app.utils.constants import BorrowingStatus, RequestStatus


class BorrowingService:
    def __init__(self):
        self.__book_service=BookService()
        self.__notification_service=NotificationService()

    def borrow_book(self, db: Session, user_id: int, borrowing_data: BorrowingCreate) -> Borrowing:
        book = self.__book_service.get_book(db, borrowing_data.book_id)

        if book.available_copies <= 0:
            self._add_to_request_queue(db,user_id=user_id, book=book)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Book is not available for borrowing"
            )

        existing_borrowing = db.query(Borrowing).filter(
            Borrowing.user_id == user_id,
            Borrowing.book_id == borrowing_data.book_id,
            Borrowing.status.in_([BorrowingStatus.BORROWED, BorrowingStatus.OVERDUE])
        ).first()

        if existing_borrowing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User already has an active borrowing for this book (ID: {existing_borrowing.borrowing_id})"
            )

        borrowing = Borrowing(
            user_id=user_id,
            book_id=borrowing_data.book_id,
            borrow_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=14),
            status=BorrowingStatus.BORROWED.value,

        )

        book.available_copies -= 1

        db.add(borrowing)
        db.commit()
        db.refresh(borrowing)

        return borrowing

    def _add_to_request_queue(self, db: Session, user_id: int, book: Book) -> BookRequestResponse:

        queue_entry = db.query(BookRequestQueue).filter(
            BookRequestQueue.user_id == user_id,
            BookRequestQueue.book_id == book.book_id,
            BookRequestQueue.status == RequestStatus.PENDING.value
        ).first()

        if queue_entry is None:

            queue_entry = BookRequestQueue(
                user_id=user_id,
                book_id=book.book_id,
                request_date=datetime.utcnow(),
                status=RequestStatus.PENDING.value,
                notification_sent=False
            )

            db.add(queue_entry)
            db.commit()
            db.refresh(queue_entry)

            book_key = f"book_request:{book.book_id}"
            book_data = {
                "title": book.title,
                "isbn": book.isbn,
                "book_id": str(book.book_id),
                "authors": ",".join([author.author.name for author in book.authors]) if book.authors else "",
                "publisher": book.publisher.name if book.publisher else "",
                "category": book.category.name if book.category else ""
            }


            self.__notification_service.redis_client.hset(book_key, mapping=book_data)


        return BookRequestResponse(
            request_id=queue_entry.request_id,
            book_id=book.book_id,
            user_id=user_id,
            request_date=queue_entry.request_date,
            status=queue_entry.status,

        )

    def update_borrowing(self, db: Session, borrowing_id: int, update_data: BorrowingUpdate) -> Borrowing:
        borrowing = db.query(Borrowing).filter(
            Borrowing.borrowing_id == borrowing_id
        ).first()

        if not borrowing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Borrowing record with ID {borrowing_id} not found"
            )

        # Handle status change
        if update_data.status:
            old_status = borrowing.status
            new_status = update_data.status

            # If changing from non-returned to returned
            if old_status != BorrowingStatus.RETURNED.value and new_status == BorrowingStatus.RETURNED.value:
                borrowing.return_date = datetime.utcnow()
                book = self.__book_service.get_book(db, borrowing.book_id)
                book.available_copies += 1

            # If changing from returned to non-returned
            elif old_status == BorrowingStatus.RETURNED.value and new_status != BorrowingStatus.RETURNED.value:
                book = self.__book_service.get_book(db, borrowing.book_id)
                book.available_copies -= 1

            borrowing.status = new_status

        # Update due date if provided
        if update_data.due_date:
            borrowing.due_date = update_data.due_date

        db.commit()
        db.refresh(borrowing)

        return borrowing

    def return_book(self, db: Session,borrowing_id: int) -> Borrowing:

        borrowing = db.query(Borrowing).filter(
            Borrowing.borrowing_id == borrowing_id
        ).first()

        if not borrowing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Borrowing record with ID {borrowing_id} not found"
            )

        if borrowing.status==BorrowingStatus.RETURNED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This book has already been returned"
            )


        borrowing.status = BorrowingStatus.RETURNED.value
        borrowing.return_date = datetime.utcnow()


        book = self.__book_service.get_book(db, borrowing.book_id)
        if book.total_copies<book.available_copies:
            book.available_copies += 1


        db.commit()
        db.refresh(borrowing)

        BackgroundTasks.add_task(
            self._process_next_request_in_queue,
            db_session=db,
            book_id=borrowing.book_id
        )

        return borrowing

    def _process_next_request_in_queue(self, db_session: Session, book_id: int) -> None:

        next_request = db_session.query(BookRequestQueue).filter(
            BookRequestQueue.book_id == book_id,
            BookRequestQueue.status == RequestStatus.PENDING.value
        ).order_by(
            BookRequestQueue.request_date
        ).first()

        if not next_request:
            return


        next_request.notification_sent = True
        db_session.commit()


        self.__notification_service.notify_book_available(
            user_id=next_request.user_id,
            book_id=book_id,
            request_id=next_request.request_id
        )

    def _update_overdue_status(self, db: Session) -> None:
        now = datetime.utcnow()
        overdue_borrowings = db.query(Borrowing).filter(
            Borrowing.status == BorrowingStatus.BORROWED,
            Borrowing.due_date < now
        ).all()
        for borrowing in overdue_borrowings:
            borrowing.status = BorrowingStatus.OVERDUE

        if overdue_borrowings:
            db.commit()

    def update_overdue_status(self, db: Session) -> int:

        now = datetime.utcnow()
        overdue_borrowings = db.query(Borrowing).filter(
            Borrowing.status == BorrowingStatus.BORROWED,
            Borrowing.due_date < now
        ).all()

        count = len(overdue_borrowings)
        for borrowing in overdue_borrowings:
            borrowing.status = BorrowingStatus.OVERDUE

        if count > 0:
            db.commit()

        return count

    def get_borrowing(self, db: Session, borrowing_id: int) -> Borrowing:

        borrowing = db.query(Borrowing).filter(
            Borrowing.borrowing_id == borrowing_id
        ).options(
            joinedload(Borrowing.book)
        ).first()

        if not borrowing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Borrowing record with ID {borrowing_id} not found"
            )

        return borrowing

    def get_user_borrowings(self, db: Session, user_id: int) -> BorrowingHistory:
        #
        author_subquery = db.query(
            BookAuthor.book_id,
            func.string_agg(Author.name, ', ').label('author_names')
        ).join(
            Author, BookAuthor.author_id == Author.author_id
        ).group_by(
            BookAuthor.book_id
        ).subquery()

        current_borrowings = db.query(
            Borrowing,
            Book.title.label("book_title"),
            author_subquery.c.author_names.label("book_authors"),
            Book.isbn.label("book_isbn")
        ).join(
            Book, Borrowing.book_id == Book.book_id
        ).outerjoin(
            author_subquery, Book.book_id == author_subquery.c.book_id
        ).filter(
            Borrowing.user_id == user_id,
            Borrowing.status.in_([BorrowingStatus.BORROWED.value, BorrowingStatus.OVERDUE.value])
        ).order_by(
            Borrowing.due_date
        ).all()

        past_borrowings = db.query(
            Borrowing,
            Book.title.label("book_title"),
            author_subquery.c.author_names.label("book_authors"),
            Book.isbn.label("book_isbn")
        ).join(
            Book, Borrowing.book_id == Book.book_id
        ).outerjoin(
            author_subquery, Book.book_id == author_subquery.c.book_id
        ).filter(
            Borrowing.user_id == user_id,
            Borrowing.status == BorrowingStatus.RETURNED.value
        ).order_by(
            desc(Borrowing.return_date)
        ).all()

        current_results = []
        for b, title, authors, isbn in current_borrowings:
            borrowing_dict = {
                **b.__dict__,
                "book_title": title,
                "book_authors": authors or "",
                "book_isbn": isbn
            }
            current_results.append(BorrowingWithBookInfo(**borrowing_dict))

        past_results = []
        for b, title, authors, isbn in past_borrowings:
            borrowing_dict = {
                **b.__dict__,
                "book_title": title,
                "book_authors": authors or "",
                "book_isbn": isbn
            }
            past_results.append(BorrowingWithBookInfo(**borrowing_dict))

        return BorrowingHistory(
            current_borrowings=current_results,
            past_borrowings=past_results
        )

    def get_overdue_borrowings(self, db: Session) -> List[BorrowingWithBookInfo]:
        print("searching")
        self._update_overdue_status(db)

        # Create a subquery to get author names for each book
        author_subquery = db.query(
            BookAuthor.book_id,
            func.string_agg(Author.name, ', ').label('author_names')
        ).join(
            Author, BookAuthor.author_id == Author.author_id
        ).group_by(
            BookAuthor.book_id
        ).subquery()

        # Query for overdue borrowings with book information
        overdue_borrowings = db.query(
            Borrowing,
            Book.title.label("book_title"),
            author_subquery.c.author_names.label("book_authors"),
            Book.isbn.label("book_isbn")
        ).join(
            Book, Borrowing.book_id == Book.book_id
        ).outerjoin(
            author_subquery, Book.book_id == author_subquery.c.book_id
        ).filter(
            Borrowing.status == BorrowingStatus.OVERDUE.value
        ).order_by(
            Borrowing.due_date
        ).all()

        # Process results
        results = []
        for row in overdue_borrowings:
            # Extract the borrowing object and additional fields
            borrowing, title, authors, isbn = row

            # Convert the SQLAlchemy model to a dictionary
            borrowing_dict = {}
            for column in borrowing.__table__.columns:
                column_name = column.name
                borrowing_dict[column_name] = getattr(borrowing, column_name)

            # Add the book information
            borrowing_dict["book_title"] = title or ""
            borrowing_dict["book_authors"] = authors or ""
            borrowing_dict["book_isbn"] = isbn or ""

            # Create the response model
            try:
                response_model = BorrowingWithBookInfo.model_validate(borrowing_dict)
                results.append(response_model)
            except Exception as e:
                print(f"Error creating BorrowingWithBookInfo: {e}")
                print(f"Data: {borrowing_dict}")

        return results

    def get_book_borrowing_history(self, db: Session, book_id: int) -> List[BorrowingWithBookInfo]:
        self.__book_service.get_book(db, book_id)

        # Define subquery to get author names as a string for each book
        author_subquery = db.query(
            BookAuthor.book_id,
            func.string_agg(Author.name, ', ').label('author_names')
        ).join(
            Author, BookAuthor.author_id == Author.author_id
        ).group_by(
            BookAuthor.book_id
        ).subquery()

        borrowings = db.query(
            Borrowing,
            Book.title.label("book_title"),
            author_subquery.c.author_names.label("book_authors"),
            Book.isbn.label("book_isbn")
        ).join(
            Book, Borrowing.book_id == Book.book_id
        ).outerjoin(
            author_subquery, Book.book_id == author_subquery.c.book_id
        ).filter(
            Borrowing.book_id == book_id
        ).order_by(
            desc(Borrowing.borrow_date)
        ).all()

        results = []
        for b, title, authors, isbn in borrowings:
            borrowing_dict = {
                **b.__dict__,
                "book_title": title,
                "book_authors": authors or "",
                "book_isbn": isbn
            }
            results.append(BorrowingWithBookInfo(**borrowing_dict))

        return results

    def list_borrowings(
            self,
            db: Session,
            user_id: Optional[int] = None,
            book_id: Optional[int] = None,
            status: Optional[str] = None,
            overdue_only: bool = False,
            sort_by: str = "borrow_date",
            sort_order: str = "desc",
            page: int = 1,
            items_per_page: int = 10
    ) -> PaginatedResponse:

        author_subquery = db.query(
            BookAuthor.book_id,
            func.string_agg(Author.name, ', ').label('author_names')
        ).join(
            Author, BookAuthor.author_id == Author.author_id
        ).group_by(
            BookAuthor.book_id
        ).subquery()

        query = db.query(
            Borrowing,
            Book.title.label("book_title"),
            author_subquery.c.author_names.label("book_authors"),
            Book.isbn.label("book_isbn")
        ).join(
            Book, Borrowing.book_id == Book.book_id
        ).outerjoin(
            author_subquery, Book.book_id == author_subquery.c.book_id
        )

        filters = []

        if user_id:
            filters.append(Borrowing.user_id == user_id)

        if book_id:
            filters.append(Borrowing.book_id == book_id)

        if status:
            filters.append(Borrowing.status == status)

        if overdue_only:
            filters.append(Borrowing.status == BorrowingStatus.OVERDUE.value)

        if filters:
            query = query.filter(and_(*filters))

        sort_column = None
        if sort_by == "borrow_date":
            sort_column = Borrowing.borrow_date
        elif sort_by == "due_date":
            sort_column = Borrowing.due_date
        elif sort_by == "return_date":
            sort_column = Borrowing.return_date

        if sort_column:
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))

        total = query.count()
        skip = (page - 1) * items_per_page
        limit = items_per_page
        has_more = (skip + limit) < total

        query = query.offset(skip).limit(limit)
        results = query.all()
        data = []
        for b, title, authors, isbn in results:
            borrowing_dict = {
                **b.__dict__,
                "book_title": title,
                "book_authors": authors or "",
                "book_isbn": isbn
            }
            data.append(BorrowingWithBookInfo(**borrowing_dict))

        return PaginatedResponse(
            data=data,
            total=total,
            skip=skip,
            limit=limit,
            has_more=has_more
        )