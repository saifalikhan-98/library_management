from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional

from app.models import Category
from app.models.book import Book, Author, Publisher, BookAuthor
from app.schemas.book import BookResponse, AuthorResponse, PublisherResponse, CategoryResponse
from app.schemas.paginated_response import PaginatedResponse, paginate_query


class BookListingService:
    def list_books(
            self,
            db: Session,
            title: Optional[str] = None,
            author_id: Optional[int] = None,
            publisher_id: Optional[int] = None,
            category_id: Optional[int] = None,
            year_from: Optional[int] = None,
            year_to: Optional[int] = None,
            available_only: bool = False,
            sort_by: str = "title",
            sort_order: str = "asc",
            page: int = 1,
            items_per_page: int = 10
    ) -> PaginatedResponse:

        query = db.query(Book).options(
            joinedload(Book.category),
            joinedload(Book.publisher),
            joinedload(Book.authors).joinedload(BookAuthor.author)
        )

        if title:
            query = query.filter(Book.title.ilike(f"%{title}%"))

        if author_id:
            query = query.join(Book.authors).filter(BookAuthor.author_id == author_id)

        if publisher_id:
            query = query.filter(Book.publisher_id == publisher_id)

        if category_id:
            query = query.filter(Book.category_id == category_id)

        if year_from:
            query = query.filter(Book.publication_year >= year_from)

        if year_to:
            query = query.filter(Book.publication_year <= year_to)

        if available_only:
            query = query.filter(Book.available_copies > 0)

        if sort_by == "title":
            query = query.order_by(Book.title.asc() if sort_order == "asc" else Book.title.desc())
        elif sort_by == "year":
            query = query.order_by(Book.publication_year.asc() if sort_order == "asc" else Book.publication_year.desc())
        elif sort_by == "added_date":
            query = query.order_by(Book.added_date.asc() if sort_order == "asc" else Book.added_date.desc())
        elif sort_by == "author":
            query = query.join(Book.authors).join(BookAuthor.author).order_by(
                Author.name.asc() if sort_order == "asc" else Author.name.desc()
            )
        elif sort_by == "publisher":
            query = query.join(Book.publisher).order_by(
                Publisher.name.asc() if sort_order == "asc" else Publisher.name.desc()
            )

        if sort_by in ["author", "publisher"]:
            from sqlalchemy.sql import select
            cte = query.with_entities(Book.book_id).distinct().cte()
            base_query = db.query(Book).options(
                joinedload(Book.category),
                joinedload(Book.publisher),
                joinedload(Book.authors).joinedload(BookAuthor.author)
            ).filter(Book.book_id.in_(select([cte.c.book_id])))
            if sort_by == "author":
                query = base_query.join(Book.authors).join(BookAuthor.author).order_by(
                    Author.name.asc() if sort_order == "asc" else Author.name.desc()
                )
            elif sort_by == "publisher":
                query = base_query.join(Book.publisher).order_by(
                    Publisher.name.asc() if sort_order == "asc" else Publisher.name.desc()
                )


        return paginate_query(query, page, items_per_page, BookResponse)

    def list_all_books(self, db:Session)->PaginatedResponse:
        query = db.query(Book).all()
        return query

    def list_authors(
            self,
            db: Session,
            name: Optional[str] = None,
            sort_by: str = "name",
            sort_order: str = "asc",
            page: int = 1,
            items_per_page: int = 10
    ) -> PaginatedResponse:
        query = db.query(Author)
        if name:
            query = query.filter(Author.name.ilike(f"%{name}%"))
        if sort_by == "name":
            query = query.order_by(Author.name.asc() if sort_order == "asc" else Author.name.desc())
        elif sort_by == "book_count":
            subquery = db.query(
                BookAuthor.author_id,
                func.count(BookAuthor.book_id).label("book_count")
            ).group_by(BookAuthor.author_id).subquery()

            query = query.outerjoin(
                subquery, Author.author_id == subquery.c.author_id
            ).order_by(
                subquery.c.book_count.asc() if sort_order == "asc" else subquery.c.book_count.desc()
            )
        return paginate_query(query, page, items_per_page, AuthorResponse)

    def list_publishers(
            self,
            db: Session,
            name: Optional[str] = None,
            sort_by: str = "name",
            sort_order: str = "asc",
            page: int = 1,
            items_per_page: int = 10
    ) -> PaginatedResponse:
        query = db.query(Publisher)
        if name:
            query = query.filter(Publisher.name.ilike(f"%{name}%"))
        if sort_by == "name":
            query = query.order_by(Publisher.name.asc() if sort_order == "asc" else Publisher.name.desc())
        elif sort_by == "book_count":
            subquery = db.query(
                Book.publisher_id,
                func.count(Book.book_id).label("book_count")
            ).group_by(Book.publisher_id).subquery()

            query = query.outerjoin(
                subquery, Publisher.publisher_id == subquery.c.publisher_id
            ).order_by(
                subquery.c.book_count.asc() if sort_order == "asc" else subquery.c.book_count.desc()
            )
        return paginate_query(query, page, items_per_page, PublisherResponse)

    def list_categories(
            self,
            db: Session,
            name: Optional[str] = None,
            sort_by: str = "name",
            sort_order: str = "asc",
            page: int = 1,
            items_per_page: int = 10
    ) -> PaginatedResponse:
        query = db.query(Category)

        if name:
            query = query.filter(Category.name.ilike(f"%{name}%"))
        if sort_by == "name":
            query = query.order_by(Category.name.asc() if sort_order == "asc" else Category.name.desc())
        elif sort_by == "book_count":

            subquery = db.query(
                Book.category_id,
                func.count(Book.book_id).label("book_count")
            ).group_by(Book.category_id).subquery()

            query = query.outerjoin(
                subquery, Category.category_id == subquery.c.category_id
            ).order_by(
                subquery.c.book_count.asc() if sort_order == "asc" else subquery.c.book_count.desc()
            )


        return paginate_query(query, page, items_per_page, CategoryResponse)
