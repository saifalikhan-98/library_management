from pydantic import BaseModel
from typing import List, Optional

class UserRoleUpdate(BaseModel):
    user_id: int
    roles: List[str]

class RoleCreate(BaseModel):
    role_name: str
    description: Optional[str] = None

class SystemStats(BaseModel):
    total_users: int
    total_books: int
    total_borrowings: int
    current_borrowings: int
    overdue_borrowings: int