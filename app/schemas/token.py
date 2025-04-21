from pydantic import BaseModel
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    roles: List[str] = []
    exp: Optional[int] = None

class RefreshToken(BaseModel):
    refresh_token: str