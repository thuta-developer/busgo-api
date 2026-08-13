import uuid
from typing import AsyncGenerator, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.token_blacklist import is_token_revoked
from app.models.user import User
from app.repositories.user_repository import UserRepository

# Swagger UI အတွက် OAuth2 Password Bearer Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async DB Session Generator Dependency"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    JWT Token ကို စစ်ဆေးပြီး Database မှ UserRepository ဖြင့် 
    User + Roles + Permissions များကို Eager Load လုပ်ယူပေးသည်။
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    # Token ကို Blacklist ထဲတွင် ရှိမရှိ စစ်ဆေးခြင်း (Logout လုပ်ထားသော Token များကို ကာကွယ်ရန်)
    if await is_token_revoked(payload):
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    # Clean Architecture အတိုင်း UserRepository ကို သုံးပြီး User အား ဆွဲယူမည်
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id_with_relations(user_id)

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    User Account သည် Active ဖြစ်မဖြစ် စစ်ဆေးပေးသည်။
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )
    return current_user


def has_permission(required_permission: str) -> Callable:
    """
    Dynamic RBAC Permission Guard Dependency Factor
    
    Usage Example:
        @router.get("/", dependencies=[Depends(has_permission("user:read"))])
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        # User ထံတွင် ရရှိထားသော Permissions များကို စုစည်းမည်
        user_permissions = set()
        for role in current_user.roles:
            for perm in role.permissions:
                user_permissions.add(perm.name)

        # တောင်းဆိုထားသော Permission မရှိပါက 403 Forbidden ပြန်မည်
        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required to perform this action",
            )
        return current_user

    return permission_checker