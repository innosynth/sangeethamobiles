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
    if user_role == RoleEnum.L1:
        users = get_users(db, email_id)

    elif user_role == RoleEnum.L2:
        L1_users = []
        L0_users = []
        users = get_users(db, email_id)
        for L1_user in users:
            L1_users = get_users(db, L1_user.email_id)
            users.extend(L1_users)
        for L0_user in L1_users:
            L0_users = get_users(db, L0_user.email_id)
            users.extend(L0_users)

    elif user_role == RoleEnum.L3:
        L2_users = []
        L1_users = []
        L0_users = []
        users = get_users(db, email_id)
        for L2_user in users:
            L2_users = get_users(db, L2_user.email_id)
            users.extend(L2_users)
        for L1_user in users:
            L1_users = get_users(db, L1_user.email_id)
            users.extend(L1_users)
        for L0_user in L1_users:
            L0_users = get_users(db, L0_user.email_id)
            users.extend(L0_users)

    elif user_role == RoleEnum.L4:
        users = get_l4_users(db, business_id)

    elif user_role == RoleEnum.L4:
        users = db.query(User).filter(user.user_id == user_id)

    if not users:
        return []
    users = list(set(users))
    user_ids = [user.user_id for user in users]
    reports_to_ids = [user.reports_to for user in users if user.reports_to]

    l0_data = db.query(L0.user_id, L0.L0_name).filter(L0.user_id.in_(user_ids)).all()
    store_map = {l0.user_id: l0.L0_name for l0 in l0_data}

    l1_data = db.query(L1.user_id, L1.L1_name).filter(L1.user_id.in_(user_ids)).all()
    area_map = {l1.user_id: l1.L1_name for l1 in l1_data}

    # Batch fetch manager names using reports_to (email_id mapping)
    managers = (
        db.query(User.email_id, User.name)
        .filter(User.email_id.in_(reports_to_ids))
        .all()
    )
    manager_map = {m.email_id: m.name for m in managers}

    # Batch fetch total recording durations, counts, and listening times
    recording_data = (
        db.query(
            VoiceRecording.user_id,
            func.sum(VoiceRecording.call_duration).label("total_duration"),
            func.sum(VoiceRecording.listening_time).label("total_listening"),
            func.count(VoiceRecording.id).label("recording_count"),
        )
        .filter(VoiceRecording.user_id.in_(user_ids))
        .group_by(VoiceRecording.user_id)
        .all()
    )
    recording_map = {rec.user_id: rec for rec in recording_data}

    user_data = []

    for user in users:
        store_name = store_map.get(user.user_id, "Unknown")
        area_name = area_map.get(user.user_id, "Unknown")
        reports_to_name = manager_map.get(user.reports_to, "Unknown")

        rec_stats = recording_map.get(user.user_id)
        recording_hours = (
            round((rec_stats.total_duration or 0) / 3600, 2) if rec_stats else 0
        )
        listening_hours = (
            round((rec_stats.total_listening or 0) / 3600, 2) if rec_stats else 0
        )
        recording_count = rec_stats.recording_count if rec_stats else 0

        user_data.append(
            UserResponse(
                user_id=user.user_id,
                name=user.name,
                email_id=user.email_id,
                user_code=user.user_code,
                user_ph_no=user.user_ph_no,
                reports_to=reports_to_name,
                business_id=user.business_id,
                role=user.role,
                store_name=store_name,
                area_name=area_name,
                created_at=user.created_at,
                modified_at=user.modified_at,
                status=user.status,
                recording_hours=recording_hours,
                recording_count=recording_count,
                listening_hours=listening_hours,
            )
        )

    return user_data
