from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.Store.StoreModel import L0
from backend.Store.StoreSchema import (
    StoreCreate,
    StoreResponse,
    StoreSummary,
    StoreUpdateSchema,
    StoreUpdateResponse,
)
from backend.Area.AreaModel import L1
from backend.db.db import get_session
from typing_extensions import Annotated
from backend.schemas.RoleSchema import RoleEnum
from backend.auth.role_checker import check_role
from backend.auth.jwt_handler import verify_token
from sqlalchemy.exc import SQLAlchemyError
from backend.User.UserModel import User

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


@router.get("/get-all-stores", response_model=list[StoreSummary])
@check_role([RoleEnum.L0, RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
async def read_stores(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):

    business_id = User.business_id

    # Fetch only stores that belong to the user's business
    stores = (
        db.query(L0)
        .join(User, L0.user_id == User.user_id)  # Join L0 with User table
        .filter(User.business_id == business_id)  # Filter by business_id
        .all()
    )

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
