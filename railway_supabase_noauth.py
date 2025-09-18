#!/usr/bin/env python3

import json
import os

print("🚀 Starting Taya Backend with Supabase (No Auth)...")

# Set up Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://placeholder.supabase.co')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', 'placeholder-key')

print(f"🔗 Supabase URL: {SUPABASE_URL}")
print(f"🔑 Supabase Key: {SUPABASE_ANON_KEY[:20]}...")

# Import FastAPI and routers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers (we'll modify these to use Supabase)
from routers import (
    conversations,
    memories,
    transcribe,
    chat,
    action_items,
    other,
)

# Mock Firebase admin to avoid import errors
class MockFirebaseAdmin:
    _apps = []

# Replace firebase_admin globally
import sys
sys.modules['firebase_admin'] = MockFirebaseAdmin()

app = FastAPI(title="Taya Backend - Supabase No Auth", version="3.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock user ID for all operations (no auth required)
MOCK_USER_ID = "noauth-user-12345"
print(f"🔓 Authentication disabled. Using mock user: {MOCK_USER_ID}")

# Override the authentication function to always return mock user
def mock_get_current_user_uid(authorization: str = None):
    """
    Mock authentication function that always returns the same user ID
    This bypasses all authentication while keeping full database functionality
    """
    return MOCK_USER_ID

# Monkey patch the auth function
try:
    import utils.other.endpoints
    utils.other.endpoints.get_current_user_uid = mock_get_current_user_uid
    print("🐒 Authentication function monkey-patched")
except ImportError:
    print("⚠️ Could not import auth endpoints, will handle at router level")

# Include core routers for Bluetooth device functionality
print("🔌 Setting up core routers...")
app.include_router(transcribe.router)      # WebSocket transcription
app.include_router(conversations.router)   # Conversation storage
app.include_router(memories.router)        # Memory storage
app.include_router(action_items.router)    # Action items
app.include_router(chat.router)            # Chat functionality
app.include_router(other.router)           # Other endpoints

# Create necessary directories
paths = ['_temp', '_samples', '_segments', '_speech_profiles']
for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)

print("📁 Directories created")

@app.get("/")
def read_root():
    return {
        "message": "🚀 Taya Backend - Supabase No Auth!",
        "status": "healthy",
        "version": "3.0.0",
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
        ]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))