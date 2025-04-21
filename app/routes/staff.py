from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session

from app.core.core_management_service import CoreManagementService
from app.database import get_db
from app.schemas.generic import GenericResponse
from app.schemas.user import PasswordUpdate, UserToken, UserPasswordUpdate
from app.security.access_level_middleware import require_role
from app.utils.constants import LIBRARIAN_ACCESS_LEVEL

router = APIRouter()


@router.get("/me", response_model=UserToken)
async def retrieve_user(current_user: UserToken = Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))):
    return current_user


@router.patch("/reset/password", response_model=GenericResponse)
async def update_password(data:UserPasswordUpdate,db:Session=Depends(get_db),
                          current_user:UserToken =Depends(require_role(min_access_level=LIBRARIAN_ACCESS_LEVEL))):
    users_service = CoreManagementService(db)
    print(current_user)
    results = users_service.update_password(user_id=current_user.user_id,
                                            password_update=data,
                                            forgot_password=False,
                                            user_email=None)
    return GenericResponse(**{"message":results})