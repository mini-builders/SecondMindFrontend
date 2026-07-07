from app.core.auth import create_access_token, hash_password, verify_password
from app.core.logger import get_logger
from app.db.client import create_user, get_user_by_id, get_user_by_mobile

logger = get_logger(__name__)


async def signup_user(name: str, mobile: str, password: str) -> dict:
    existing = await get_user_by_mobile(mobile)
    if existing:
        raise ValueError("This mobile number is already registered.")

    password_hash = hash_password(password)
    user = await create_user(name, mobile, password_hash)
    token = create_access_token(str(user["_id"]))

    logger.info("New user registered | mobile=%s | name=%s", mobile, name)
    return {"access_token": token, "token_type": "bearer", "user_name": name, "user_id": str(user["_id"])}


async def login_user(mobile: str, password: str) -> dict:
    user = await get_user_by_mobile(mobile)
    if not user or not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid mobile number or password.")

    token = create_access_token(str(user["_id"]))

    logger.info("User logged in | mobile=%s", mobile)
    return {"access_token": token, "token_type": "bearer", "user_name": user["name"], "user_id": str(user["_id"])}


async def change_password(user_id: str, current_password: str, new_password: str) -> None:
    from bson import ObjectId
    from app.db.client import get_users_collection

    user = await get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    if not verify_password(current_password, user["password_hash"]):
        raise ValueError("Current password is incorrect.")
    if verify_password(new_password, user["password_hash"]):
        raise ValueError("New password must be different from current password.")

    new_hash = hash_password(new_password)
    await get_users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": new_hash}},
    )
    logger.info("Password changed | user_id=%s", user_id)
