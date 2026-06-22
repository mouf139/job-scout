from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.models.pipeline_run import PipelineRun
from app.schemas.user import UserCreate, UserOut, UserUpdate, UserAdminView
from app.services.auth import hash_password, require_admin, get_current_user, create_access_token

router = APIRouter()


@router.get("/", response_model=list[UserAdminView])
async def list_users(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    user_views = []
    for u in users:
        last_run_result = await db.execute(
            select(PipelineRun)
            .where(PipelineRun.user_id == u.id)
            .order_by(PipelineRun.started_at.desc())
            .limit(1)
        )
        last_run = last_run_result.scalar_one_or_none()

        jobs_result = await db.execute(
            select(func.coalesce(func.sum(PipelineRun.jobs_found), 0))
            .where(PipelineRun.user_id == u.id)
        )
        resumes_result = await db.execute(
            select(func.coalesce(func.sum(PipelineRun.resumes_generated), 0))
            .where(PipelineRun.user_id == u.id)
        )

        user_views.append(UserAdminView(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role.value,
            is_active=u.is_active,
            must_change_password=u.must_change_password,
            onboarding_completed=u.onboarding_completed,
            created_at=u.created_at,
            last_login=u.last_login,
            jobs_found=jobs_result.scalar() or 0,
            resumes_generated=resumes_result.scalar() or 0,
            last_run=last_run.started_at if last_run else None,
            last_error=last_run.errors if last_run and last_run.status == "failed" else None,
        ))
    return user_views


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(req: UserCreate, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=req.name,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=UserRole.user,
        must_change_password=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    req: UserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if req.name is not None:
        user.name = req.name
    if req.email is not None:
        user.email = req.email
    if req.is_active is not None:
        user.is_active = req.is_active

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == UserRole.admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete admin user")

    await db.delete(user)
    await db.commit()


@router.post("/{user_id}/impersonate")
async def impersonate_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    token = create_access_token(user.id, user.role.value)
    return {"access_token": token, "impersonating": user.name}
