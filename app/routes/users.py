from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginCredentials
from app.schemas.generic import GenericResponse
from app.schemas.token import Token

from app.security.access_level_middleware import require_role
from app.services.user_service import UserService
from app.schemas.user import UserResponse, UserCreate, KeyResponse, UserToken, UserUpdate, UserInDB, UserPasswordUpdate
from app.utils.constants import API_KEY_HEADER, USER_ACCESS_LEVEL

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(user_data:UserCreate, db: Session = Depends(get_db)):
    user_service = UserService(db)
    results=user_service.create_candidate_user(user_create=user_data)
    return results

@router.post("/reset-key/{username}", response_model=KeyResponse)
async def reset_key(username:str, db:Session=Depends(get_db)):
    user_service =UserService(db)
    results=user_service.reset_api_key(username)
    return {'api_key':results}

@router.post("/login", response_model=Token)
async def login_user(login_creds:LoginCredentials, api_key: str = Header(..., alias=API_KEY_HEADER), db:Session=Depends(get_db)):
    users_service=UserService(db)
    results=users_service.user_login(api_key=api_key, username=login_creds.username, password=login_creds.password)
    return results

@router.get("/", response_model=UserToken)
async def get_user_details(db: Session = Depends(get_db),
                           api_key: str = Header(..., alias=API_KEY_HEADER),
                           current_user =  Depends(require_role(min_access_level=USER_ACCESS_LEVEL, api_key_required=True))):
    return current_user

@router.patch("/", response_model=UserInDB)
async def update_user_details(data:UserUpdate,db:Session=Depends(get_db),api_key: str = Header(..., alias=API_KEY_HEADER),
                              current_user =  Depends(require_role(min_access_level=USER_ACCESS_LEVEL, api_key_required=True))):
    users_service=UserService(db=db)
    results=users_service.update(user_id=current_user.user_id, user_update=data)
    return results

@router.patch("/reset/password", response_model=GenericResponse)
async def update_password(data:UserPasswordUpdate,db:Session=Depends(get_db),api_key: str = Header(..., alias=API_KEY_HEADER),
                          current_user =  Depends(require_role(min_access_level=USER_ACCESS_LEVEL, api_key_required=True))):
    users_service=UserService(db)
    results=users_service.update_user_password(user_id=current_user.user_id,api_key=api_key, update_password=data)
    return results
