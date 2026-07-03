from app.core.auth import create_access_token, hash_password, verify_password
from app.core.logger import get_logger
from app.db.client import create_user, get_user_by_mobile

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
