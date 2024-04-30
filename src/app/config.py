from functools import lru_cache
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    api_email: str
    api_password: str
    auth0_domain: str
    auth0_api_audience: str
    auth0_algorithms: str
    auth0_client_id: str
    auth0_client_secret: str
    auth0_management_token: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    load_dotenv()
    return Settings(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        api_email=os.getenv("API_EMAIL"),
        api_password=os.getenv("API_PASSWORD"),
        auth0_domain=os.getenv("AUTH0_DOMAIN"),
        auth0_api_audience=os.getenv("AUTH0_API_AUDIENCE"),
        auth0_algorithms=os.getenv("AUTH0_ALGORITHMS"),
        auth0_client_id=os.getenv("AUTH0_CLIENT_ID"),
        auth0_client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
        auth0_management_token=os.getenv("AUTH0_MANAGEMENT_TOKEN")
    )


def get_metadata():
    return [
        {
            "name": "Container",
        },
        {
            "name": "Client"
        }
    ]
