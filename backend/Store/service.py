from backend.Store.StoreModel import L0
from backend.User.service import extract_users


def extract_stores(business_id, user_id, role, db):
    users = extract_users(user_id, role, db)
    stores = []
    for user in users:
        store = db.query(L0).filter(L0.user_id == user.user_id).all()
        stores.extend(store)

    return stores
