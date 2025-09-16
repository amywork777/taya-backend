import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import firebase_admin
from fastapi import FastAPI

# Initialize Firebase with minimal configuration
try:
    if os.environ.get('SERVICE_ACCOUNT_JSON'):
        service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
        credentials = firebase_admin.credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(credentials)
    else:
        # For local development without full Firebase setup
        print("Warning: Firebase not configured. Some features may not work.")
except Exception as e:
    print(f"Firebase initialization failed: {e}")

app = FastAPI(title="Taya Backend", version="1.0.0")

# Basic routers that should work without complex dependencies
from routers import (
    other,
    simple_test,
    auth_oauth,
    # Add more routers as needed when dependencies are configured
)

app.include_router(other.router)
app.include_router(simple_test.router)
app.include_router(auth_oauth.router)

@app.get("/")
async def root():
    return {"message": "Taya Backend is running!", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "taya-backend"}

# Create required directories
paths = ['_temp', '_samples', '_segments', '_speech_profiles']
for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)