from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.generic import GenericResponse
from app.schemas.librarian import LibrarianCreate
from app.schemas.paginated_response import PaginatedResponse
from app.schemas.user import UserCreate, UserToken, UserResponse, UserInDB
from app.security.access_level_middleware import require_role
from app.services.admin_services import AdminServices
from app.utils.constants import ADMIN_ACCESS_LEVEL

router = APIRouter()


@router.post("/register/staff", response_model=LibrarianCreate)
async def register_user(user_data:UserCreate, db: Session = Depends(get_db),
               current_user:UserToken= Depends(require_role(min_access_level=ADMIN_ACCESS_LEVEL))):
    user_service=AdminServices(db)
    results=user_service.add_staff(user_data=user_data)
    """
        Once staff is registered we can further logic where creds are sent to staff email for staff access
    """
    return results


@router.put("/staff/{user_id}/deactivate", response_model=GenericResponse)
async def deactivate_staff(user_id: int = Path(..., description="ID of the staff member to deactivate"),
                  db: Session = Depends(get_db),
                  current_user: UserToken = Depends(require_role(min_access_level=ADMIN_ACCESS_LEVEL))):
    user_service = AdminServices(db)
    results = user_service.deactivate_staff(user_id=user_id)
    return results


@router.put("/staff/{user_id}/reactivate", response_model=GenericResponse)
async def reactivate_staff(user_id: int = Path(..., description="ID of the staff member to reactivate"),
                   db: Session = Depends(get_db),
                   current_user: UserToken = Depends(require_role(min_access_level=ADMIN_ACCESS_LEVEL))):
    user_service = AdminServices(db)
    results = user_service.reactivate_staff(user_id=user_id)
    return results


@router.put("/user/{user_id}/reassign-role", response_model=GenericResponse)
async def reassign_user_role(user_id: int = Path(..., description="ID of the user to reassign role"),
                     db: Session = Depends(get_db),
                     current_user: UserToken = Depends(require_role(min_access_level=ADMIN_ACCESS_LEVEL))):
    user_service = AdminServices(db)
    results = user_service.reassign_user_role(user_id=user_id)
    return results


@router.get("/users", response_model=PaginatedResponse[UserInDB])
async def list_users(
        skip: int = Query(0, ge=0, description="Number of users to skip for pagination"),
        limit: int = Query(100, ge=1, le=500, description="Maximum number of users to return"),
        is_active: Optional[bool] = Query(None, description="Filter users by active status"),
        role_type: Optional[str] = Query(None,
                                         description="Filter by role type: 'staff', 'admin', 'candidate', or leave empty for all"),
        db: Session = Depends(get_db),
        _: UserToken = Depends(require_role(min_access_level=ADMIN_ACCESS_LEVEL))
):
    user_service = AdminServices(db)
    results = user_service.list_users(
        skip=skip,
        limit=limit,
        is_active=is_active,
        role_type=role_type
    )
    return results

@router.get("/users/{user_id}", response_model=UserInDB)
async def retrieve_user(
                            user_id: int = Path(..., description="ID of the staff member to reactivate"),
                            current_user: UserToken = Depends(require_role(min_access_level=ADMIN_ACCESS_LEVEL)),
                            db: Session = Depends(get_db),
                        ):
    user_service=AdminServices(db=db)
    return user_service.retrieve_user(user_id=user_id)

@router.get("/me", response_model=UserToken)
async def retrieve_user(current_user: UserToken = Depends(require_role(min_access_level=ADMIN_ACCESS_LEVEL))):

    return current_user






