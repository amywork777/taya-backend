import json
import os
import firebase_admin
from fastapi import FastAPI
from routers import (
    workflow,
    chat,
    firmware,
    plugins,
    transcribe,
    notifications,
    speech_profile,
    agents,
    users,
    trends,
    sync,
    apps,
    custom_auth,
    payment,
    integration,
    conversations,
    memories,
    mcp,
    oauth,
    auth,
    action_items,
    other,
)
from utils.other.timeout import TimeoutMiddleware

# Fix SERVICE_ACCOUNT_JSON issue - use base64 credentials instead
os.environ["SERVICE_ACCOUNT_JSON"] = ""  # Clear the broken one

# Initialize Firebase with base64 credentials
if not firebase_admin._apps:
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_BASE64'):
        # Decode base64 service account for Railway
        import base64
        service_account_info = json.loads(base64.b64decode(os.environ["GOOGLE_APPLICATION_CREDENTIALS_BASE64"]).decode())
        credentials = firebase_admin.credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(credentials)
        # Set the proper SERVICE_ACCOUNT_JSON for database client
        os.environ["SERVICE_ACCOUNT_JSON"] = json.dumps(service_account_info)
    else:
        firebase_admin.initialize_app()

app = FastAPI(title="Taya Backend - Full Features No Auth", version="1.0.0")

# Mock user ID for all operations (no auth required)
MOCK_USER_ID = "noauth-user-12345"

# Override the authentication function to always return mock user
def mock_get_current_user_uid(authorization: str = None):
    """
    Mock authentication function that always returns the same user ID
    This bypasses all authentication while keeping full database functionality
    """
    return MOCK_USER_ID

# Monkey patch the auth function
import utils.other.endpoints
utils.other.endpoints.get_current_user_uid = mock_get_current_user_uid

# Include all routers (full backend functionality)
app.include_router(transcribe.router)
app.include_router(conversations.router)
app.include_router(action_items.router)
app.include_router(memories.router)
app.include_router(chat.router)
app.include_router(plugins.router)
app.include_router(speech_profile.router)
app.include_router(notifications.router)
app.include_router(workflow.router)
app.include_router(integration.router)
app.include_router(agents.router)
app.include_router(users.router)
app.include_router(trends.router)
app.include_router(other.router)
app.include_router(firmware.router)
app.include_router(sync.router)
app.include_router(apps.router)
app.include_router(custom_auth.router)
app.include_router(oauth.router)
app.include_router(auth.router)
app.include_router(payment.router)
app.include_router(mcp.router)

# Add timeout middleware
methods_timeout = {
    "GET": os.environ.get('HTTP_GET_TIMEOUT', '30'),
    "PUT": os.environ.get('HTTP_PUT_TIMEOUT', '60'),
    "PATCH": os.environ.get('HTTP_PATCH_TIMEOUT', '60'),
    "DELETE": os.environ.get('HTTP_DELETE_TIMEOUT', '30'),
}

app.add_middleware(TimeoutMiddleware, methods_timeout=methods_timeout)

# Create necessary directories
paths = ['_temp', '_samples', '_segments', '_speech_profiles']
for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)

@app.get("/")
def read_root():
    return {"message": "Taya Backend - Full Features No Auth!", "status": "healthy", "user_id": MOCK_USER_ID}

@app.get("/health")
def health_check():
    return {"status": "healthy", "auth_disabled": True, "mock_user": MOCK_USER_ID}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))