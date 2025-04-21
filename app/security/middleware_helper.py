from datetime import datetime

import jwt
from fastapi import HTTPException
from jose import jwt, JWTError
from app.config import settings
from dateutil import parser as parser

from app.models import UserApiKey
from app.schemas.user import UserToken

class MiddlewareHelper:


    def validate_jwt(self,token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")


    def candidate_key_validation(self,api_key, payload)->bool:
        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid Api Key")

        if payload.get("role") != 1:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        key_hash = payload.get("key_hash", None)
        key_expires_at = payload.get("key_expires_at", None)
        if key_hash is None or key_expires_at is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        key_expires_at = parser.parse(str(key_expires_at))
        now = datetime.utcnow()
        if key_expires_at < now:
            raise HTTPException(status_code=401, detail="Api Key has expired, Please generate a new one")

        verify_key = UserApiKey.verify_key(api_key, key_hash)

        if not verify_key:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return True


    def return_user_model(self,payload)->UserToken:
        return UserToken(**payload)



    def current_user(self,token):
        payload=self.validate_jwt(token)
        return self.return_user_model(payload)
