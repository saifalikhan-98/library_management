from sqlalchemy.orm import Session

from app.models import User
from app.core.core_management_service import CoreManagementService
from fastapi import HTTPException, status

from app.utils.common_utils import create_access_token


class StaffService(CoreManagementService):

    def __init__(self, db: Session):
        super().__init__(db)

    def staff_login(self,username: str, password: str):
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        if not self.verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        token_data = self.create_token_data(user)
        access_token, expires_in = create_access_token(token_data
                                                       )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in.__str__()
        }
