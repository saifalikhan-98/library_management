from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as user_router
from .admin import router as admin_router
from .staff import router as staff_router
from .book import router as book_router
from .borrowing import router as borrowing_router

router=APIRouter()
router.include_router(auth_router,prefix="/auth", tags=["authentication"])
router.include_router(user_router, prefix="/user", tags=["users"])
router.include_router(admin_router,prefix="/admin", tags=["admin"])
router.include_router(staff_router,prefix="/staff", tags=["staff"])
router.include_router(book_router,prefix="/book", tags=["book"])
router.include_router(borrowing_router, prefix="/borrow", tags=["borrow"])
