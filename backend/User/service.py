from fastapi import HTTPException
from backend.User.UserModel import User
from backend.Store.StoreModel import L0
from backend.Area.AreaModel import L1
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.schemas.RoleSchema import RoleEnum
from sqlalchemy import func
from backend.User.UserSchema import UserResponse


def get_users(db, email_id):
    users = db.query(User).filter(User.reports_to == email_id).all()
    return users


# def get_l2_users(db, email_id):
#     users = db.query(User).filter(User.reports_to == email_id).all()
#     return users


# def get_l3_users(db, email_id):
#     users = db.query(User).filter(User.reports_to == email_id).all()
#     return users


def get_l4_users(db, business_id):
    users = db.query(User).filter(User.business_id == business_id).all()
    return users


def extract_users(user_id, user_role, db):
    current_user = (
        db.query(User.business_id, User.email_id)
        .filter(User.user_id == user_id)
        .first()
    )

    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    business_id = current_user.business_id
    email_id = current_user.email_id

    # Fetch all users in one optimized query
    def fetch_users(email_ids):
        return db.query(User).filter(User.reports_to.in_(email_ids)).all()

    users = []
    email_ids = [email_id]

    if user_role == RoleEnum.L1:
        users = fetch_users(email_ids)

    elif user_role == RoleEnum.L2:
        L1_users = fetch_users(email_ids)
        email_ids = [user.email_id for user in L1_users]
        L0_users = fetch_users(email_ids)
        users = L1_users + L0_users

    elif user_role == RoleEnum.L3:
        L2_users = fetch_users(email_ids)
        email_ids = [user.email_id for user in L2_users]
        L1_users = fetch_users(email_ids)
        email_ids = [user.email_id for user in L1_users]
        L0_users = fetch_users(email_ids)
        users = L2_users + L1_users + L0_users

    elif user_role == RoleEnum.L4:
        users = get_l4_users(db, business_id)

    if not users:
        return []

    # Remove duplicates and extract user IDs
    users = list({user.user_id: user for user in users}.values())  
    user_ids = [user.user_id for user in users]
    reports_to_ids = list(set(user.reports_to for user in users if user.reports_to))

    # Batch fetch all necessary data in one go
    store_map = {
        l0.user_id: l0.L0_name
        for l0 in db.query(L0.user_id, L0.L0_name).filter(L0.user_id.in_(user_ids)).all()
    }

    area_map = {
        l1.user_id: l1.L1_name
        for l1 in db.query(L1.user_id, L1.L1_name).filter(L1.user_id.in_(user_ids)).all()
    }

    manager_map = {
        m.email_id: m.name
        for m in db.query(User.email_id, User.name).filter(User.email_id.in_(reports_to_ids)).all()
    }

    recording_map = {
        rec.user_id: rec
        for rec in db.query(
            VoiceRecording.user_id,
            func.sum(VoiceRecording.call_duration).label("total_duration"),
            func.sum(VoiceRecording.listening_time).label("total_listening"),
            func.count(VoiceRecording.id).label("recording_count"),
        )
        .filter(VoiceRecording.user_id.in_(user_ids))
        .group_by(VoiceRecording.user_id)
        .all()
    }

    # Construct user response
    user_data = [
        UserResponse(
            user_id=user.user_id,
            name=user.name,
            email_id=user.email_id,
            user_code=user.user_code,
            user_ph_no=user.user_ph_no,
            reports_to=manager_map.get(user.reports_to, "Unknown"),
            business_id=user.business_id,
            role=user.role,
            store_name=store_map.get(user.user_id, "Unknown"),
            area_name=area_map.get(user.user_id, "Unknown"),
            created_at=user.created_at,
            modified_at=user.modified_at,
            status=user.status,
            recording_hours=round((recording_map.get(user.user_id).total_duration or 0) / 3600, 2)
                if user.user_id in recording_map else 0,
            recording_count=recording_map.get(user.user_id).recording_count if user.user_id in recording_map else 0,
            listening_hours=round((recording_map.get(user.user_id).total_listening or 0) / 3600, 2)
                if user.user_id in recording_map else 0,
        )
        for user in users
    ]


    return user_data
