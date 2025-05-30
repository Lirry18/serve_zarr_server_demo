from pydantic import BaseSettings, AnyHttpUrl

class Settings(BaseSettings):
    supabase_url: AnyHttpUrl
    supabase_anon_key: str

    cors_origins: list[str]

    class Config:
        env_file = ".env"

settings = Settings()