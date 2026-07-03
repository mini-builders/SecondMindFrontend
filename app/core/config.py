from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    app_env: str = "development"
    log_level: str = "INFO"
    mongodb_uri: str
    mongodb_database: str = "secondmind"
    secret_key: str
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_claim_email: str = ""

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
