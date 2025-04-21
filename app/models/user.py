from sqlalchemy import Integer, Column, ForeignKey, String, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_joined = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

    # Foreign key to role - single role per user
    role_id = Column(Integer, ForeignKey("roles.role_id"))

    # Relationship - single role per user
    role = relationship("Role", back_populates="users")
    borrowings = relationship("Borrowing", back_populates="user", cascade="all, delete-orphan")
    user_keys = relationship("UserApiKey", back_populates="user", cascade="all, delete-orphan")
    book_requests = relationship("BookRequestQueue", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"

