from fastapi import APIRouter
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from backend.db.db import get_session
from backend.Business.BusinessModel import Business
from backend.Business.BusinessSchema import BusinessCreate

router = APIRouter()

@router.post("/create-business")
def create_business(
    business_id: str,
    business_name: str, 
    business_status: str,
    created_at: datetime,
    modified_at: datetime,
    db: Session = Depends(get_session)
):
    """ Create a new business. """
    new_business = Business(
        business_id=business_id,
        business_name=business_name,
        business_status=business_status,
        created_at=created_at,
        modified_at=modified_at
    )
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    return {"message": "Business created", "business_id": new_business.business_id}

@router.get("/businesses")
def get_businesses(db: Session = Depends(get_session)):
    """ Get all businesses. """
    businesses = db.query(Business).all()
    return {"businesses": businesses}
