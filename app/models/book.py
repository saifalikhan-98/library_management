from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Author(Base):
    __tablename__ = "authors"

    author_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    biography = Column(Text)

    #relationships
    books = relationship("BookAuthor", back_populates="author")

    def __repr__(self):
        return f"<Author {self.name}>"


class Publisher(Base):
    __tablename__ = "publishers"

    publisher_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    address = Column(String(255))
    contact_info = Column(String(255))

    #relationships
    books = relationship("Book", back_populates="publisher")

    def __repr__(self):
        return f"<Publisher {self.name}>"


# Many-to-many relationship for books and authors
class BookAuthor(Base):
    __tablename__ = "book_authors"

    book_id = Column(Integer, ForeignKey("books.book_id"), primary_key=True)
    author_id = Column(Integer, ForeignKey("authors.author_id"), primary_key=True)

    #relationships
    book = relationship("Book", back_populates="authors")
    author = relationship("Author", back_populates="books")

    def __repr__(self):
        return f"<BookAuthor {self.book_id}:{self.author_id}>"


class Book(Base):
    __tablename__ = "books"

    book_id = Column(Integer, primary_key=True)
    isbn = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    publisher_id = Column(Integer, ForeignKey("publishers.publisher_id"), index=True)
    publication_year = Column(Integer)
    description = Column(Text)
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
    added_date = Column(DateTime, default=datetime.utcnow)
    category_id = Column(Integer, ForeignKey("categories.category_id"), index=True)

    #relationships
    publisher = relationship("Publisher", back_populates="books")
    category = relationship("Category", back_populates="books")
    authors = relationship("BookAuthor", back_populates="book")
    borrowings = relationship("Borrowing", back_populates="book")

    request_queue = relationship("BookRequestQueue", back_populates="book")

    def __repr__(self):
        return f"<Book {self.title}>"

