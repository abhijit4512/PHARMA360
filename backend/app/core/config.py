from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "PHARMA360 API"
    environment: str = "development"
    database_url: str = "sqlite:///./pharma360.db"
    jwt_secret: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    superadmin_email: str = "admin@pharma360.local"
    superadmin_password: str = "ChangeMe123!"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
