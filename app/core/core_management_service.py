from datetime import datetime

import bcrypt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from app.models.user import User
from app.models.role import Role

from app.schemas.user import UserUpdate, UserPasswordUpdate, UserInDB, PasswordUpdate, UserCreate, UserResponse
from app.services.user_api_key_service import UserApiKeyService

from abc import ABC

from app.utils.constants import LIBRARIAN_ACCESS_LEVEL


class CoreManagementService(ABC):
    def __init__(self, db: Session):
        self.db = db
        self.api_key_service=UserApiKeyService()

    def get_user_by_id(self, user_id: int) -> User:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"user not found"
            )

        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_all_users(
            self,
            skip: int = 0,
            limit: int = 100,
            is_active: Optional[bool] = None
    ) -> List[User]:
        query = self.db.query(User)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    def get_all_staff(self,skip: int = 0,limit: int = 100,is_active: Optional[bool] = None) -> List[User]:
        query = self.db.query(User)

        if is_active is not None:
            query = query.filter(User.is_active == is_active,
                                 User.role.access_level==LIBRARIAN_ACCESS_LEVEL)

        return query.offset(skip).limit(limit).all()

    def update(self, user_id: int, user_update: UserUpdate) -> UserInDB:
        db_user = self.get_user_by_id(user_id)

        update_data = user_update.model_dump()
        for key, value in update_data.items():
            setattr(db_user, key, value)

        self.db.commit()
        self.db.refresh(db_user)
        user_response = UserInDB.model_validate(db_user)
        return user_response

    def update_password(self, user_id: int, password_update: UserPasswordUpdate|PasswordUpdate, forgot_password:bool=False, user_email:str=None) -> str:

        if forgot_password:
            db_user = self.get_user_by_email(user_email)
        else:
            db_user = self.get_user_by_id(user_id)
            if not self.verify_password(password_update.current_password, db_user.password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incorrect current password"
                )

        hashed_password = self.get_password_hash(password_update.new_password)
        db_user.password = hashed_password

        self.db.commit()
        self.db.refresh(db_user)
        return "password updated successfully"



    def delete(self, user_id: int) -> User:
        db_user = self.get_user_by_id(user_id)
        self.db.delete(db_user)
        self.db.commit()
        return db_user

    def reassign_role(self, user_id: int, access_level: int) -> User:
        db_user = self.get_user_by_id(user_id)

        role = self.db.query(Role).filter(Role.access_level == access_level).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with access level '{access_level}' not found"
            )

        db_user.role_id=role.role_id
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def remove_role(self, user_id: int, role_name: str) -> User:
        db_user = self.get_user_by_id(user_id)

        role = self.db.query(Role).filter(Role.role_name == role_name).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_name}' not found"
            )

        if role not in db_user.roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User doesn't have role '{role_name}'"
            )

        db_user.roles.remove(role)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def deactivate(self, user_id: int) -> User:
        db_user = self.get_user_by_id(user_id)
        db_user.is_active = False
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def reactivate(self, user_id: int) -> User:
        db_user = self.get_user_by_id(user_id)

        db_user.is_active = True
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    @staticmethod
    def has_role(user: User, role_name: str) -> bool:
        return any(role.role_name == role_name for role in user.roles)

    def create_token_data(self,user: User) -> dict:
        return {
            "first_name":user.first_name,
            "last_name":user.last_name,
            "username": user.username,
            "user_id": user.user_id,
            "email": user.email,
            "role": user.role.access_level,
        }

    def get_password_hash(self, password: str) -> str:
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(password_bytes, salt)
        return hash.decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        user_bytes = plain_password.encode('utf-8')
        result = bcrypt.checkpw(user_bytes, hashed_password.encode('utf-8'))
        return result

    def create_user(self, user_create: UserCreate, access_level:int) -> User:
        db_user = self.get_user_by_username(user_create.username)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        db_user = self.get_user_by_email(user_create.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        hashed_password = self.get_password_hash(user_create.password)
        user_role = self.db.query(Role).filter(Role.access_level == access_level).first()
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            password=hashed_password,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            date_joined=datetime.utcnow(),
            is_active=True,
            role_id=user_role.role_id
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user