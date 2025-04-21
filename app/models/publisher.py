from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Publisher(Base):
    __tablename__ = "publisher"

    publisher_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True)
    isbn = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(100), nullable=False, index=True)
    publisher = Column(String(100))
    publication_year = Column(Integer)
    category_id = Column(Integer, ForeignKey("categories.category_id", ondelete="SET NULL"), index=True)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)
    added_date = Column(DateTime, default=func.now())
    description = Column(Text)

    #relationships
    category = relationship("Category", back_populates="books")
    borrowings = relationship("Borrowing", back_populates="book", cascade="all, delete-orphan")

    #constraints
    __table_args__ = (
        CheckConstraint('available_copies >= 0 AND available_copies <= total_copies',
                        name='valid_copies'),
    )

    def __repr__(self):
        return f"<Book {self.title}>"