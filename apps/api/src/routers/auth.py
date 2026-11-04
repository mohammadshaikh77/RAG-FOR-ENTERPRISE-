import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.auth.deps import get_current_user, require_admin
from apps.api.src.auth.security import create_access_token, get_password_hash, verify_password
from apps.api.src.db.session import get_db
from apps.api.src.models.organization import Organization
from apps.api.src.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-Tenancy"])


EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=100)
    org_slug: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str


class CreateMemberRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.MEMBER


class OrganizationDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class UserResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    organization: OrganizationDetailResponse | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Registers a new tenant organization along with its primary administrator account."""
    # Check if org slug already exists
    stmt = select(Organization).where(Organization.slug == payload.org_slug)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization slug '{payload.org_slug}' is already taken",
        )

    # Check if email exists
    stmt_user = select(User).where(User.email == payload.email)
    result_user = await db.execute(stmt_user)
    if result_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{payload.email}' already exists",
        )

    # Create Organization
    org = Organization(
        id=uuid.uuid4(),
        name=payload.org_name,
        slug=payload.org_slug,
    )
    db.add(org)
    await db.flush()

    # Create Admin User
    user = User(
        id=uuid.uuid4(),
        org_id=org.id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        data={
            "sub": str(user.id),
            "org_id": str(user.org_id),
            "role": user.role.value,
            "email": user.email,
        }
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            org_id=user.org_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticates credentials and returns a tenant-scoped JWT token."""
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    token = create_access_token(
        data={
            "sub": str(user.id),
            "org_id": str(user.org_id),
            "role": user.role.value,
            "email": user.email,
        }
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            org_id=user.org_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Returns the authenticated user's profile and organization context."""
    org_stmt = select(Organization).where(Organization.id == current_user.org_id)
    org_result = await db.execute(org_stmt)
    org = org_result.scalar_one_or_none()
    org_detail = (
        OrganizationDetailResponse(id=org.id, name=org.name, slug=org.slug) if org else None
    )

    return UserResponse(
        id=current_user.id,
        org_id=current_user.org_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        organization=org_detail,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_organization_member(
    payload: CreateMemberRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Admin-only endpoint to add new members to their organization."""
    stmt_user = select(User).where(User.email == payload.email)
    result_user = await db.execute(stmt_user)
    if result_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{payload.email}' already exists",
        )

    new_user = User(
        id=uuid.uuid4(),
        org_id=admin_user.org_id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        org_id=new_user.org_id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role.value,
        is_active=new_user.is_active,
    )
