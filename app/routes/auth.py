from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.generic import GenericResponse
from app.schemas.user import PasswordUpdate
from app.services.staff_auth_service import StaffService
from app.schemas.auth import LoginCredentials
from app.schemas.token import Token
from app.core.core_management_service import CoreManagementService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_user(user_data:LoginCredentials, db: Session = Depends(get_db)):
    user_service=StaffService(db)
    results=user_service.staff_login(username=user_data.username, password=user_data.password)
    return results


@router.patch("/forgot/password", response_model=GenericResponse)
async def forgot_password(data:PasswordUpdate,email: str = Query(None, min_length=1, max_length=50, description="Enter user email"),db:Session=Depends(get_db)):
    users_service=CoreManagementService(db)
    results=users_service.update_password(user_id=None,
                                          password_update=data,
                                          forgot_password=True,
                                          user_email=email)
    return GenericResponse(**{"message":results})
