import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserResponse, UserUpdate, UserWithRolesResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users Management"])


@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    dependencies=[Depends(has_permission("user:read"))],
)
async def list_users(
    search: Optional[str] = Query(None, description="Search by Name, Email, or Phone"),
    account_type: Optional[str] = Query(None, description="Filter by customer or staff"),
    is_active: Optional[bool] = Query(None, description="Filter active/inactive"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search, Filter & Paginated User List API
    """
    service = UserService(db)
    return await service.get_users_list(
        search=search,
        account_type=account_type,
        is_active=is_active,
        page=page,
        size=size,
    )


@router.get(
    "/{user_id}",
    response_model=UserWithRolesResponse,
    dependencies=[Depends(has_permission("user:read"))],
)
async def get_user_detail(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Get Single User Detail by ID
    """
    service = UserService(db)
    return await service.get_user_with_roles_by_id(user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(has_permission("user:update"))],
)
async def update_user(
    user_id: uuid.UUID, user_in: UserUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Update User Information
    """
    service = UserService(db)
    return await service.update_user(user_id, user_in)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("user:delete"))],
)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete User by ID
    """
    service = UserService(db)
    return await service.delete_user(user_id)