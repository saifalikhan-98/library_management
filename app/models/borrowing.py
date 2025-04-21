from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Borrowing(Base):
    __tablename__ = "borrowings"

    borrowing_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    book_id = Column(Integer, ForeignKey("books.book_id", ondelete="CASCADE"), index=True)
    borrow_date = Column(DateTime, default=func.now())
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="borrowed", index=True)  # 'borrowed', 'returned', 'overdue'

    #relationships
    user = relationship("User", back_populates="borrowings")
    book = relationship("Book", back_populates="borrowings")

    # constraints
    __table_args__ = (
        CheckConstraint('return_date IS NULL OR return_date >= borrow_date',
                        name='valid_return_date'),
    )

    def __repr__(self):
        return f"<Borrowing {self.borrowing_id}>"