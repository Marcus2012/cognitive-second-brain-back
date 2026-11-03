from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AuditEvent, Membership, Role, User, Workspace
from app.schemas import (
    AuditOut,
    Login,
    MemberAdd,
    MemberOut,
    Register,
    Token,
    UserOut,
    WorkspaceCreate,
    WorkspaceOut,
)
from app.security import current_user, dummy_hash, issue_token, passwords

router = APIRouter(prefix="/api/v1")


def audit(db, user, action, resource_id, workspace_id=None, **details):
    db.add(
        AuditEvent(
            actor_id=user.id,
            action=action,
            resource_id=resource_id,
            workspace_id=workspace_id,
            details=details,
        )
    )


def membership(
    workspace_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Membership:
    member = db.scalar(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user.id,
        )
    )
    if member is None:
        raise HTTPException(404, "Workspace not found")
    return member


def manager(member: Membership = Depends(membership)) -> Membership:
    if member.role not in (Role.owner.value, Role.admin.value):
        raise HTTPException(403, "Owner or admin role required")
    return member


@router.post("/auth/register", response_model=UserOut, status_code=201, tags=["auth"])
def register(data: Register, db: Session = Depends(get_db)):
    user = User(
        email=str(data.email).lower(), name=data.name, password_hash=passwords.hash(data.password)
    )
    db.add(user)
    try:
        db.flush()
        audit(db, user, "user.registered", user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered") from None
    return user


@router.post("/auth/login", response_model=Token, tags=["auth"])
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = passwords.verify(data.password, user.password_hash if user else dummy_hash)
    if not valid or not user or not user.is_active:
        raise HTTPException(
            401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"}
        )
    audit(db, user, "user.login", user.id)
    db.commit()
    return Token(
        access_token=issue_token(user), expires_in=get_settings().access_token_minutes * 60
    )


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(current_user)):
    return user


@router.post("/workspaces", response_model=WorkspaceOut, status_code=201, tags=["workspaces"])
def create_workspace(
    data: WorkspaceCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    workspace = Workspace(name=data.name)
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=Role.owner.value))
    audit(db, user, "workspace.created", workspace.id, workspace.id)
    db.commit()
    return workspace


@router.get("/workspaces", response_model=list[WorkspaceOut], tags=["workspaces"])
def list_workspaces(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return db.scalars(
        select(Workspace)
        .join(Membership)
        .where(
            Membership.user_id == user.id,
        )
        .order_by(Workspace.created_at, Workspace.id)
        .limit(limit)
        .offset(offset)
    ).all()


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceOut, tags=["workspaces"])
def get_workspace(member: Membership = Depends(membership), db: Session = Depends(get_db)):
    return db.get(Workspace, member.workspace_id)


@router.get("/workspaces/{workspace_id}/members", response_model=list[MemberOut], tags=["members"])
def list_members(
    member: Membership = Depends(membership),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return db.scalars(
        select(Membership)
        .where(
            Membership.workspace_id == member.workspace_id,
        )
        .order_by(Membership.created_at, Membership.id)
        .limit(limit)
        .offset(offset)
    ).all()


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=MemberOut,
    status_code=201,
    tags=["members"],
)
def add_member(
    data: MemberAdd,
    member: Membership = Depends(manager),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Ownership transfer is deliberately a separate future operation.
    if data.role == Role.owner or (data.role == Role.admin and member.role != Role.owner):
        raise HTTPException(403, "Cannot grant this role")
    target = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if not target or not target.is_active:
        raise HTTPException(404, "Registered user not found")
    added = Membership(workspace_id=member.workspace_id, user_id=target.id, role=data.role.value)
    db.add(added)
    try:
        db.flush()
        audit(
            db,
            user,
            "member.added",
            added.id,
            member.workspace_id,
            user_id=target.id,
            role=data.role.value,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "User already belongs to workspace") from None
    return added


@router.get("/workspaces/{workspace_id}/audit", response_model=list[AuditOut], tags=["audit"])
def list_audit(
    member: Membership = Depends(manager),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.workspace_id == member.workspace_id,
        )
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id)
        .limit(limit)
        .offset(offset)
    ).all()
