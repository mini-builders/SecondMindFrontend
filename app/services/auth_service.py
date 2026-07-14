from app.core.auth import create_access_token, hash_password, verify_password
from app.core.logger import get_logger
from app.db.client import create_user, get_user_by_id, get_user_by_mobile

logger = get_logger(__name__)


def _normalize_mobile(mobile: str) -> str:
    """Normalize to E.164: strips spaces/dashes, adds +91 for bare 10-digit Indian numbers."""
    mobile = mobile.strip().replace(" ", "").replace("-", "")
    if mobile.startswith("+"):
        return mobile
    if len(mobile) == 10:
        return f"+91{mobile}"
    if len(mobile) == 12 and mobile.startswith("91"):
        return f"+{mobile}"
    return f"+{mobile}"


async def signup_user(name: str, mobile: str, password: str) -> dict:
    mobile = _normalize_mobile(mobile)
    existing = await get_user_by_mobile(mobile)
    if existing:
        raise ValueError("This mobile number is already registered.")

    password_hash = hash_password(password)
    user = await create_user(name, mobile, password_hash)
    token = create_access_token(str(user["_id"]))

    logger.info("New user registered | mobile=%s | name=%s", mobile, name)
    return {"access_token": token, "token_type": "bearer", "user_name": name, "user_id": str(user["_id"])}


async def login_user(mobile: str, password: str) -> dict:
    user = await get_user_by_mobile(_normalize_mobile(mobile))
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


async def get_profile(user_id: str) -> dict:
    user = await get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    return {
        "name": user.get("name", ""),
        "mobile": user.get("mobile", ""),
        "email": user.get("email") or "",
    }


async def update_profile(user_id: str, name: str | None, email: str | None, mobile: str | None) -> dict:
    from bson import ObjectId
    from app.db.client import get_users_collection

    user = await get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")

    update_data: dict = {}
    if name is not None:
        update_data["name"] = name.strip()
    if email is not None:
        update_data["email"] = email.strip()
    if mobile is not None:
        mobile = _normalize_mobile(mobile)
        if mobile != user.get("mobile"):
            existing = await get_user_by_mobile(mobile)
            if existing:
                raise ValueError("This mobile number is already in use.")
        update_data["mobile"] = mobile

    if update_data:
        await get_users_collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
        )
        logger.info("Profile updated | user_id=%s | fields=%s", user_id, list(update_data.keys()))

    updated_user = await get_user_by_id(user_id)
    return {
        "name": updated_user.get("name", ""),
        "mobile": updated_user.get("mobile", ""),
        "email": updated_user.get("email") or "",
    }
