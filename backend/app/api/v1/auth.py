from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.tenant import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.auth import TenantRegister, TenantLogin, TokenResponse, TenantInfo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: TenantRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Tenant).where(Tenant.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    tenant = Tenant(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(tenant)
    await db.flush()

    token = create_access_token(str(tenant.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(data: TenantLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.email == data.email))
    tenant = result.scalar_one_or_none()

    if not tenant or not verify_password(data.password, tenant.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(str(tenant.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=TenantInfo)
async def get_me(tenant: Tenant = Depends(get_current_tenant)):
    return TenantInfo(
        id=str(tenant.id),
        name=tenant.name,
        email=tenant.email,
        is_active=tenant.is_active,
    )
