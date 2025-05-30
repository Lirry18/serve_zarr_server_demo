from supabase import create_client

url        = "https://lgzgbxxrxeqjsqcuwyyf.supabase.co"
anon_key   = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxnemdieHhyeGVxanNxY3V3eXlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg2MTA1OTMsImV4cCI6MjA2NDE4NjU5M30.eauDYNBqY-_Ydx9h3qD39k7lOrTVLd4u5gYJP7MhZac"
supabase   = create_client(url, anon_key)

def login(email: str, password: str):
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
    print(res)
    if res.get("error"):
        raise Exception(res["error"]["message"])
    token = res["data"]["session"]["access_token"]
    return token

print(login("l.pinter@ascenscia.ai","Peertjee1!"))