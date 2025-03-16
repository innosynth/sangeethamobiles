from functools import wraps
from fastapi import HTTPException, Depends
from backend.auth.jwt_handler import verify_token
from backend.schemas.RoleSchema import RoleEnum


def check_role(allowed_roles: list[RoleEnum]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            token_data = kwargs.get("token")
            role_str = token_data.get("role")  # e.g., "L0"
            try:
                # Remove the "L" prefix and convert to int, then create the RoleEnum
                role_int = int(role_str.lstrip("L"))
                user_role = RoleEnum(role_int)
            except (ValueError, KeyError):
                raise HTTPException(
                    status_code=403, detail="Invalid user role provided in token."
                )

            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to perform this action",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
