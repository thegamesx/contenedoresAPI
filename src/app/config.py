from functools import lru_cache
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    auth0_domain: str
    auth0_api_audience: str
    auth0_issuer: str
    auth0_algorithms: str
    auth0_client_id: str
    auth0_client_secret: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings(
        auth0_domain=os.getenv("AUTH0_DOMAIN"),
        auth0_api_audience=os.getenv("AUTH0_API_AUDIENCE"),
        auth0_issuer=os.getenv("AUTH0_ISSUER"),
        auth0_algorithms=os.getenv("AUTH0_ALGORITHMS"),
        auth0_client_id=os.getenv("AUTH0_CLIENT_ID"),
        auth0_client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY")
    )
