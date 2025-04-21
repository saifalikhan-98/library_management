import secrets

import bcrypt
from sqlalchemy import Integer, Column, ForeignKey, String, DateTime, func, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class UserApiKey(Base):

    __tablename__ = "user_keys"


    api_key_id=Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    #relationship
    user = relationship("User", back_populates="user_keys")

    @staticmethod
    def generate_api_key():
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_key(api_key):
        key_bytes = api_key.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(key_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_key(api_key, hashed_key):
        key_bytes = api_key.encode('utf-8')
        hashed_bytes = hashed_key.encode('utf-8')
        return bcrypt.checkpw(key_bytes, hashed_bytes)