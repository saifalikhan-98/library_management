from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Index,Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BookRequestQueue(Base):
    __tablename__ = "book_request_queue"

    request_id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.book_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    request_date = Column(DateTime, default=func.now(), nullable=False)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, FULFILLED, CANCELLED
    notification_sent = Column(Boolean, default=False)

    # Relationships
    book = relationship("Book", back_populates="request_queue")
    user = relationship("User", back_populates="book_requests")

    # Create an index for fast queue retrieval by book_id and status
    __table_args__ = (
        Index('idx_book_status_date', book_id, status, request_date),
    )