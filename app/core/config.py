from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    app_env: str = "development"
    log_level: str = "INFO"
    mongodb_uri: str
    mongodb_database: str = "secondmind"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
