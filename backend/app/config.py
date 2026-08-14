"""
config.py — Application settings, loaded from environment variables via pydantic-settings.
All secrets must be present in .env (gitignored). No defaults for sensitive values.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    database_url: str = Field(..., description="asyncpg connection string for Supabase Postgres")
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_role_key: str = Field(..., description="Supabase service-role key — NEVER expose to frontend")

    # --- LLM ---
    llm_provider: str = Field(default="gemini", description="'gemini' or 'anthropic'")
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key (optional)")

    # --- WhatsApp ---
    whatsapp_cloud_api_token: str = Field(default="", description="Meta Cloud API bearer token")
    whatsapp_phone_number_id: str = Field(default="", description="Meta Phone Number ID")
    whatsapp_verify_token: str = Field(default="", description="Arbitrary token for webhook verification")

    # --- Auth ---
    jwt_secret: str = Field(..., description="HS256 JWT signing secret — generate with secrets.token_hex(32)")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7, description="7 days default")
    otp_provider: str = Field(default="whatsapp", description="OTP delivery method")

    # --- Runtime ---
    env: str = Field(default="development", description="'development' | 'production'")


# Singleton — import this everywhere, do not construct Settings() again per request
settings = Settings()
