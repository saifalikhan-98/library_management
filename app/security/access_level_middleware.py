from fastapi import Depends, HTTPException, Request, Header
from app.security.get_token import get_token
from app.security.middleware_helper import MiddlewareHelper
from app.utils.constants import API_KEY_HEADER, USER_ACCESS_LEVEL
from app.schemas.user import UserToken

class RoleBasedAccessMiddleware:

    def __init__(self):
        self.__helper=MiddlewareHelper()

    async def verify_access(self,request: Request,token: str,
                            api_key: str|None,min_access_level: int = 3,
                            verify_api_key: bool = True
                            ) -> UserToken:
        payload = self.__helper.validate_jwt(token)

        user_role = payload.get("role")
        if user_role is None:
            raise HTTPException(status_code=401, detail="Invalid user role")

        if user_role < min_access_level:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions"
            )

        if verify_api_key:
            if not api_key:
                raise HTTPException(status_code=401, detail="Invalid Api Key")
            self.__helper.candidate_key_validation(api_key=api_key, payload=payload)

        user = self.__helper.return_user_model(payload=payload)
        return user


role_middleware = RoleBasedAccessMiddleware()


def require_role(min_access_level: int = USER_ACCESS_LEVEL, api_key_required:bool=False):
    if min_access_level==USER_ACCESS_LEVEL and api_key_required:
        async def dependency(
                request: Request,
                token: str = Depends(get_token),
                api_key: str = Header(..., alias=API_KEY_HEADER)
        ):
            return await role_middleware.verify_access(
                request=request,
                token=token,
                api_key=api_key,
                min_access_level=min_access_level,
                verify_api_key=True
            )

        return dependency
    else:
        async def dependency(
                request: Request,
                token: str = Depends(get_token)
        ):
            return await role_middleware.verify_access(
                request=request,
                token=token,
                api_key=None,
                min_access_level=min_access_level,
                verify_api_key=False
            )

        return dependency

