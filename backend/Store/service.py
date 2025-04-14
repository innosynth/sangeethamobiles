from backend.Store.StoreModel import L0
from backend.User.service import extract_users, get_user_ids_by_hierarchy


def extract_stores(business_id, user_id, role, db):
    # Get user IDs from the extract_users function without creating full user objects
    user_ids = get_user_ids_by_hierarchy(user_id, role, db)
    
    # Fetch all stores for all users in a single query instead of multiple queries
    stores = db.query(L0).filter(L0.user_id.in_(user_ids)).all()
    
    return stores
