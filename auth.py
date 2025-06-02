from supabase import create_client
from fastapi import HTTPException
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv
load_dotenv(".env")

url        = os.getenv("SUPABASE_URL")
anon_key   = os.getenv("SUPABASE_ANON_KEY")

security = HTTPBearer()

def get_supabase_client():
    return create_client(url, anon_key)

## Reads the bearer token from the header, validate and return
async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security), sb = Depends(get_supabase_client)):
    try:
        res = sb.auth.get_user(creds.credentials)
    except Exception:
        raise HTTPException(401, "Invalid or expired token")

    user = getattr(res, "user", None)
    if not user or getattr(user, "email_confirmed_at", None) is None:
        raise HTTPException(401, "Invalid or unconfirmed user")
    return user


## Logs in with username pw credentials at Supabase, returns API Accesstoken
def login(email: str, password: str) -> str:
    supabase = get_supabase_client()
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {e}")

    token = res.session.access_token
    if not token:
        raise HTTPException(401, "Login did not return an access token")
    return token