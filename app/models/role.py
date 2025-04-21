from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


"""
Roles details

3: this is to define admin who has all access
2: Librarian level access
1: user level access, access to only borrow or return books
"""
class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(20), unique=True, nullable=False)
    access_level = Column(Integer, default=3)
    description = Column(String(255))

    # Relationship - one-to-many (one role can be assigned to many users)
    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role {self.role_name}>"