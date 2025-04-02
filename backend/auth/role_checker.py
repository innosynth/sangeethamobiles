from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, Depends
from backend.auth.jwt_handler import verify_token
from backend.schemas.RoleSchema import RoleEnum


def check_role(allowed_roles: list[RoleEnum]):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            token_data = kwargs.get("token")
            if not token_data:
                raise HTTPException(status_code=401, detail="Missing token data")

            role_str = token_data.get("role")
            try:
                user_role = RoleEnum(role_str)
            except (ValueError, KeyError):
                raise HTTPException(
                    status_code=403, detail="Invalid user role provided in token."
                )

            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to perform this action",
                )

            # Handle both async and sync functions
            result = func(*args, **kwargs)
            if hasattr(result, "_await_"):  # Check if it's a coroutine
                return await result
            return result

        return wrapper

    return decorator
