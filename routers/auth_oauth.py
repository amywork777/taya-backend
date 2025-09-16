from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
import os
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
import secrets
from utils.redis_client import redis_client
import json

router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/auth/google/callback")

# OAuth scopes - what info we want from Google
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

def create_google_oauth_flow():
    """Create Google OAuth flow"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    return flow

@router.get("/google/login")
async def google_login():
    """Initiate Google OAuth login"""
    try:
        flow = create_google_oauth_flow()

        # Generate state parameter for security
        state = secrets.token_urlsafe(32)

        # Store state in Redis for verification (expires in 10 minutes)
        if redis_client.is_available():
            redis_client.set(f"oauth_state:{state}", "pending", expire=600)

        # Get authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )

        return {
            "authorization_url": authorization_url,
            "state": state,
            "message": "Redirect user to authorization_url"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth setup failed: {str(e)}")

@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        # Get authorization code and state from callback
        authorization_code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')

        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

        if not authorization_code or not state:
            raise HTTPException(status_code=400, detail="Missing authorization code or state")

        # Verify state parameter
        if redis_client.is_available():
            stored_state = redis_client.get(f"oauth_state:{state}")
            if not stored_state:
                raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
            redis_client.delete(f"oauth_state:{state}")

        # Exchange authorization code for tokens
        flow = create_google_oauth_flow()
        flow.fetch_token(code=authorization_code)

        # Get user info from Google
        credentials = flow.credentials
        user_info_request = GoogleRequest()
        credentials.refresh(user_info_request)

        # Get user profile info
        import requests
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        user_info = user_info_response.json()

        # Generate session token
        session_token = secrets.token_urlsafe(32)

        # Store user session in Redis (expires in 24 hours)
        if redis_client.is_available():
            session_data = {
                "user_id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "provider": "google"
            }
            redis_client.set(f"session:{session_token}", session_data, expire=86400)

        return {
            "message": "Authentication successful",
            "session_token": session_token,
            "user": {
                "id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.get("/verify")
async def verify_session(request: Request):
    """Verify user session token"""
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    session_token = auth_header.split("Bearer ")[1]

    if not redis_client.is_available():
        raise HTTPException(status_code=503, detail="Session service unavailable")

    # Get session data from Redis
    session_data = redis_client.get(f"session:{session_token}")
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {
        "valid": True,
        "user": session_data
    }

@router.post("/logout")
async def logout(request: Request):
    """Logout user and invalidate session"""
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    session_token = auth_header.split("Bearer ")[1]

    if redis_client.is_available():
        redis_client.delete(f"session:{session_token}")

    return {"message": "Logged out successfully"}

@router.get("/status")
async def auth_status():
    """Check OAuth configuration status"""
    return {
        "google_oauth": {
            "configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
            "client_id_present": bool(GOOGLE_CLIENT_ID),
            "redirect_uri": GOOGLE_REDIRECT_URI
        },
        "redis_available": redis_client.is_available(),
        "scopes": SCOPES
    }