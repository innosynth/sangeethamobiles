from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.Feedback.FeedbackModel import FeedbackModel
from backend.Store.StoreModel import L0
from backend.Store.StoreSchema import (
    RegionRequest,
    RegionResponse,
    StoreCreate,
    StoreResponse,
    StoreSummary,
    StoreUpdateSchema,
    StoreUpdateResponse,
)
from typing import List, Optional
from backend.Area.AreaModel import L1
from backend.User.service import extract_users
from backend.db.db import get_session
from typing_extensions import Annotated
from backend.sales.SalesModel import L2
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.role_checker import check_role
from backend.auth.jwt_handler import verify_token
from sqlalchemy.exc import SQLAlchemyError
from backend.User.UserModel import User
from backend.Store.service import extract_stores

router = APIRouter()


@router.post("/create-store", response_model=StoreResponse)
@check_role([RoleEnum.L4])
async def create_store(
    store: StoreCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    db_store = L0(
        L0_name=store.store_name,
        L0_code=store.store_code,
        L0_addr=store.store_address,
        user_id=token.get("user_id"),  # Extracting user_id from token
        status=store.store_status,
    )

    db.add(db_store)
    db.commit()
    db.refresh(db_store)

    return StoreResponse(
        store_id=db_store.L0_id,
        store_name=db_store.L0_name,
        store_code=db_store.L0_code,
        store_address=db_store.L0_addr,
        store_status=db_store.status,
        created_at=db_store.created_at,
        modified_at=db_store.modified_at,
    )


@router.get("/get-all-stores", response_model=List[StoreSummary])
# @check_role([RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
async def read_stores(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    user_role = token.get("role")
    business_id = User.business_id

    stores = extract_stores(business_id, user_id, user_role, db)

    return [
        StoreSummary(
            L0_id=store.L0_id,
            L0_name=store.L0_name,
            L0_code=store.L0_code,
            L0_addr=store.L0_addr,
            user_id=store.user_id,
            status=store.status,
            created_at=store.created_at,
            modified_at=store.modified_at,
        )
        for store in stores
    ]


@router.get("/get-store-region", response_model=RegionResponse)
def get_store_region(
    region_id: Optional[str] = Query(None, description="Regional ID"),
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    role = token.get("role")

    if user_id is None or role is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    role_enum = RoleEnum(role)

    if role_enum == RoleEnum.L2:
        l2 = db.query(L2).filter(L2.user_id == user_id).first()
        if not l2:
            raise HTTPException(status_code=404, detail="L2 region not found")
        region_id = l2.L2_id

    if region_id:
        l2 = db.query(L2).filter(L2.L2_id == region_id).first()
        if not l2:
            raise HTTPException(status_code=404, detail="Region not found.")
        l2_user_id = l2.user_id
        downline_users = extract_users(l2_user_id, RoleEnum.L2, db)
    else:
        downline_users = extract_users(user_id, role_enum, db)

    seen = set()
    users = []
    for user in downline_users:
        if user.user_id not in seen:
            seen.add(user.user_id)
            users.append(user)

    user_ids = [user.user_id for user in users]
    user_emails = [user.email_id for user in users]

    stores = (
        db.query(L0.L0_name)
        .filter(L0.user_id.in_(user_ids))
        .distinct()
        .all()
    )
    store_names = [store.L0_name for store in stores]

    total_seconds = db.query(func.sum(VoiceRecording.call_duration)).filter(
        VoiceRecording.user_id.in_(user_ids)
    ).scalar() or 0

    total_recordings = db.query(func.count(VoiceRecording.id)).filter(
        VoiceRecording.user_id.in_(user_ids)
    ).scalar() or 0

    avg_duration = db.query(func.avg(VoiceRecording.call_duration)).filter(
        VoiceRecording.user_id.in_(user_ids)
    ).scalar()

    audio_ids = db.query(VoiceRecording.id).filter(
        VoiceRecording.user_id.in_(user_ids)
    ).subquery()

    total_feedbacks = db.query(func.count(FeedbackModel.id)).filter(
        FeedbackModel.audio_id.in_(audio_ids)
    ).scalar()

    return RegionResponse(
        Stores=store_names,
        Users=user_emails,
        total_recordings=total_recordings,
        total_hours=round(total_seconds / 3600, 2),
        average_call_duration_minutes=round(avg_duration / 60, 2) if avg_duration else 0.0,
        total_feedbacks=total_feedbacks,
    )

@router.put("/edit-store/{L0_id}", response_model=StoreUpdateResponse)
@check_role([RoleEnum.L4])  # Ensuring only L4 users can edit stores
async def edit_store(
    L0_id: str,
    store_update: StoreUpdateSchema,  # Updated schema
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):

    try:
        store = (
            db.query(L0)
            .filter(
                L0.L0_id == L0_id,
                L0.user_id
                == token[
                    "user_id"
                ],  # Ensuring user can only edit their business stores
            )
            .first()
        )

        if not store:
            raise HTTPException(
                status_code=404, detail="Store not found or unauthorized access"
            )

        if store_update.L0_code and store_update.L0_code != store.L0_code:
            existing_store = (
                db.query(L0)
                .filter(L0.L0_code == store_update.L0_code, L0.L0_id != L0_id)
                .first()
            )
            if existing_store:
                raise HTTPException(
                    status_code=400, detail="Store code already in use by another store"
                )

        update_data = store_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(store, field, value)
        db.commit()
        db.refresh(store)
        return StoreUpdateResponse(
            message="Store updated successfully",
            store_id=store.L0_id,
            updated_fields=list(update_data.keys()),
        )
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Database error while updating store"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/delete-store/{L0_id}", response_model=dict)
@check_role([RoleEnum.L4])
async def delete_store(
    L0_id: str,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        store = (
            db.query(L0)
            .filter(
                L0.L0_id == L0_id,
                L0.user_id
                == token[
                    "user_id"
                ],  # Ensuring only stores of this user's business can be deleted
            )
            .first()
        )

        if not store:
            raise HTTPException(
                status_code=404, detail="Store not found or unauthorized access"
            )

        db.delete(store)
        db.commit()
        return {"message": "Store deleted successfully", "store_id": L0_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting store: {str(e)}")
