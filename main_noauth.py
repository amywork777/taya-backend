#!/usr/bin/env python3

import json
import os

print("🚀 Starting Taya Backend with Supabase (No Auth)...")

# Set up Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://placeholder.supabase.co')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', 'placeholder-key')

print(f"🔗 Supabase URL: {SUPABASE_URL}")
print(f"🔑 Supabase Key: {SUPABASE_ANON_KEY[:20]}...")

# Do not monkey-patch firebase_admin; rely on dependency overrides only

# Mock user ID for all operations (no auth required)
MOCK_USER_ID = "noauth-user-12345"
print(f"🔓 Authentication disabled. Using mock user: {MOCK_USER_ID}")

# Import Header for correct dependency signature
from fastapi import Header

# Override the authentication function to always return mock user
def mock_get_current_user_uid(authorization: str = Header(None)):
    """
    Mock authentication function that always returns the same user ID
    This bypasses all authentication while keeping full database functionality
    """
    print(f"🔓 Authentication bypassed, returning mock user: {MOCK_USER_ID}")
    return MOCK_USER_ID

# Configure environment variables to allow ADMIN_KEY bypass if any code paths rely on it
os.environ['LOCAL_DEVELOPMENT'] = 'true'
os.environ['ADMIN_KEY'] = 'BYPASS_AUTH_'
print("🔧 Environment variables set for auth bypass")

# Import FastAPI and routers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers AFTER monkey-patching
from routers import (
    conversations,
    memories,
    transcribe,
    chat,
    action_items,
    other,
    users,
    speech_profile,
    apps,
)

app = FastAPI(title="Taya Backend - Supabase No Auth", version="3.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Override dependencies using FastAPI's dependency override system
from utils.other.endpoints import get_current_user_uid as real_get_current_user_uid
from dependencies import get_current_user_id as real_get_current_user_id
from dependencies import get_uid_from_mcp_api_key as real_get_uid_from_mcp_api_key

app.dependency_overrides[real_get_current_user_uid] = mock_get_current_user_uid

async def _mock_get_current_user_id(*args, **kwargs):
    return MOCK_USER_ID

async def _mock_get_uid_from_mcp_api_key(*args, **kwargs):
    return MOCK_USER_ID

app.dependency_overrides[real_get_current_user_id] = _mock_get_current_user_id
app.dependency_overrides[real_get_uid_from_mcp_api_key] = _mock_get_uid_from_mcp_api_key
print("🔧 FastAPI dependency overrides applied for all auth entrypoints")

# Include core routers for Bluetooth device functionality
print("🔌 Setting up core routers...")
app.include_router(transcribe.router)      # WebSocket transcription
app.include_router(conversations.router)   # Conversation storage
app.include_router(memories.router)        # Memory storage
app.include_router(action_items.router)    # Action items
app.include_router(chat.router)            # Chat functionality
app.include_router(other.router)           # Other endpoints
app.include_router(users.router)           # User endpoints
app.include_router(speech_profile.router)  # Speech profile endpoints
app.include_router(apps.router)            # Apps endpoints

# Create necessary directories
paths = ['_temp', '_samples', '_segments', '_speech_profiles']
for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)

print("📁 Directories created")

@app.get("/")
def read_root():
    return {
        "message": "🚀 Taya Backend - Supabase No Auth DEPLOYED!",
        "status": "healthy",
        "version": "3.0.1",
        "database": "Supabase",
        "user_id": MOCK_USER_ID,
        "auth_disabled": True,
        "supabase_url": SUPABASE_URL,
        "features": [
            "Supabase PostgreSQL storage",
            "Real Deepgram transcription",
            "Complete AI processing",
            "No authentication required",
            "WebSocket support for Bluetooth devices"
        ],
        "test_endpoints": [
            "/v1/users/profile-noauth",
            "/v1/conversations-noauth"
        ]
    }

@app.get("/v1/users/profile-noauth")
def get_user_profile_noauth():
    """Test endpoint to verify backend functionality without auth."""
    from database.users import get_user_profile
    try:
        profile = get_user_profile(MOCK_USER_ID)
        if not profile:
            # Create a basic profile if none exists
            return {
                "uid": MOCK_USER_ID,
                "email": "noauth@example.com",
                "name": "No Auth User",
                "auth_disabled": True,
                "created_with_no_auth": True
            }
        return profile
    except Exception as e:
        return {
            "error": str(e),
            "uid": MOCK_USER_ID,
            "auth_disabled": True,
            "message": "Profile function working but may need database setup"
        }

@app.get("/v1/conversations-noauth")
def get_conversations_noauth():
    """Test endpoint to get conversations without auth."""
    from database import conversations as conversations_db
    try:
        conversations = conversations_db.get_conversations(MOCK_USER_ID, limit=10, offset=0)
        return {
            "conversations": conversations,
            "user_id": MOCK_USER_ID,
            "auth_disabled": True,
            "count": len(conversations) if conversations else 0
        }
    except Exception as e:
        return {
            "error": str(e),
            "user_id": MOCK_USER_ID,
            "auth_disabled": True,
            "message": "Conversations function working but may need database setup"
        }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "auth_disabled": True,
        "mock_user": MOCK_USER_ID,
        "database": "supabase",
        "supabase_connected": bool(SUPABASE_URL and SUPABASE_ANON_KEY)
    }

@app.get("/v1/health")
def health_check_v1():
    return {"status": "ok", "database": "supabase"}

print("🎉 Taya Backend - Supabase No Auth - Ready!")

@app.get("/test-deployment-working")
def test_deployment():
    return {"message": "Supabase no-auth deployment is working!", "file": "main_noauth.py", "version": "3.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))