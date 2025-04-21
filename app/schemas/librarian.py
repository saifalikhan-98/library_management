from datetime import datetime
from app.schemas.user import UserBase


class LibrarianCreate(UserBase):
    user_id: int
    date_joined: datetime
    is_active: bool

    class Config:
        orm_mode = True