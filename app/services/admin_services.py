from typing import Optional

from sqlalchemy.orm import Session

from app.models import User
from app.schemas.generic import GenericResponse
from app.schemas.librarian import LibrarianCreate
from app.schemas.paginated_response import PaginatedResponse
from app.schemas.user import UserCreate, UserInDB
from app.core.core_management_service import CoreManagementService
from app.utils.constants import LIBRARIAN_ACCESS_LEVEL, ADMIN_ACCESS_LEVEL, USER_ACCESS_LEVEL


class AdminServices(CoreManagementService):

    def __init__(self, db:Session):
        super().__init__(db)

    def add_staff(self, user_data:UserCreate)->LibrarianCreate:
        db_user=self.create_user(user_create=user_data,  access_level=LIBRARIAN_ACCESS_LEVEL)
        return db_user

    def deactivate_staff(self, user_id)->GenericResponse:
        self.deactivate(user_id=user_id)
        return GenericResponse(**{"message":"Staff deactivated successfully"})

    def reactivate_staff(self, user_id: int)->GenericResponse:
        self.reactivate(user_id=user_id)
        return GenericResponse(**{"message":"Staff deactivated successfully"})

    def reassign_user_role(self, user_id)->GenericResponse:
        """
            This method can be used to change roles in future in new roles are introduced ,
            currently we only support candidate-3, librarian-2 , admin-1 roles
        """
        self.reassign_role(user_id=user_id, access_level=2)
        return GenericResponse(**{"message": "Role reassigned successfully"})

    def list_users(
            self,
            skip: int = 0,
            limit: int = 100,
            is_active: Optional[bool] = None,
            role_type: Optional[str] = None
    ) -> PaginatedResponse:

        query = self.db.query(User)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if role_type:
            if role_type.lower() == 'staff':
                query = query.filter(User.role_id == LIBRARIAN_ACCESS_LEVEL)
            elif role_type.lower() == 'admin':
                query = query.filter(User.role_id == ADMIN_ACCESS_LEVEL)
            elif role_type.lower() == 'candidate':
                query = query.filter(User.role_id == USER_ACCESS_LEVEL)


        total_count = query.count()
        users = query.offset(skip).limit(limit).all()
        user_responses = [UserInDB.model_validate(user) for user in users]
        return PaginatedResponse(
            data=user_responses,
            total=total_count,
            skip=skip,
            limit=limit,
            has_more=total_count > (skip + limit)
        )


    def retrieve_user(self, user_id)->UserInDB:
        return self.get_user_by_id(user_id)