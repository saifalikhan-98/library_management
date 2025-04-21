from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.generic import GenericResponse
from app.schemas.user import UserCreate, UserResponse, UserInDB, UserPasswordUpdate, PasswordUpdate
from app.core.core_management_service import CoreManagementService
from app.utils.common_utils import create_access_token
from app.utils.constants import USER_ACCESS_LEVEL, ADMIN_ACCESS_LEVEL, LIBRARIAN_ACCESS_LEVEL


class UserService(CoreManagementService):

    def __init__(self, db:Session):
        super().__init__(db=db)

    def reset_api_key(self, username: str) -> str:
        """
            In production there will a additional MFA check before api key is reset for a user
        """
        db_user = self.get_user_by_username(username)
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username not found"
            )
        if db_user.role.access_level in [ADMIN_ACCESS_LEVEL, LIBRARIAN_ACCESS_LEVEL]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Action not allowed"
            )

        api_key = self.api_key_service.reset_api_key(db_user,self.db)
        return api_key

    def user_login(self, api_key: str, username: str, password: str):
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        verified_api_key, msg,api_key = self.api_key_service.validate_api_key(api_key=api_key, user_id=user.user_id, db=self.db)

        if not verified_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=msg
            )

        if not self.verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        token_data = self.create_token_data(user)
        token_data['key_hash']=api_key.key_hash
        token_data['key_expires_at']=api_key.expires_at.__str__()

        access_token, expires_in = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in.__str__()
        }

    def create_candidate_user(self, user_create: UserCreate) -> UserResponse:
        db_user = self.create_user(user_create=user_create, access_level=USER_ACCESS_LEVEL)
        api_key=self.api_key_service.create_api_key_mapping(db_user,db=self.db)
        user_response = UserInDB.model_validate(db_user)
        results = user_response.model_dump()
        results['api_key'] = api_key
        return UserResponse(**results)

    def update_user_password(self, user_id:int, api_key:str, update_password:UserPasswordUpdate|PasswordUpdate, forgot_password:bool=False,
                             user_email:str=None)->GenericResponse:

        if forgot_password:
           user=self.get_user_by_email(user_email)
           if not user:
               raise HTTPException(
                   status_code=status.HTTP_401_UNAUTHORIZED,
                   detail="Incorrect username or password"
               )
        else:
            user = self.get_user_by_id(user_id=user_id)


            verified_api_key, msg, api_key = self.api_key_service.validate_api_key(api_key=api_key, user_id=user.user_id,
                                                                               db=self.db)

            if not verified_api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=msg
                )
        response=self.update_password(user_id=user_id,
                                      password_update=update_password,
                                      forgot_password=forgot_password,
                                      user_email=user_email)
        return GenericResponse(**{"message":response})


