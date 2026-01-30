import os
from functools import lru_cache

from supabase import create_client, Client


@lru_cache()
def get_supabase() -> Client:
    pass
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

    return create_client(url, key)
