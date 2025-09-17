from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="Taya Backend - No Auth", version="1.0.0")

# Enable CORS for web/mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple test data
FAKE_CONVERSATIONS = [
    {
        "id": "test-1",
        "title": "Test Conversation",
        "overview": "This is a test conversation without authentication",
        "emoji": "🤖",
        "category": "test",
        "created_at": "2025-09-17T00:00:00Z",  # ✅ REQUIRED by mobile app
        "started_at": "2025-09-17T00:00:00Z",  # ✅ REQUIRED by mobile app
        "finished_at": "2025-09-17T00:05:00Z", # ✅ REQUIRED by mobile app
        "structured": {                         # ✅ REQUIRED by mobile app
            "title": "Test Conversation",
            "overview": "This is a test conversation without authentication",
            "emoji": "🤖",
            "category": "test",
            "action_items": [
                {"description": "Test the new backend", "completed": False}
            ],
            "events": []
        },
        "transcript_segments": [
            {"text": "Hello world", "speaker": "SPEAKER_0", "start": 0.0, "end": 2.0}
        ],
        "action_items": [
            {"description": "Test the new backend", "completed": False}
        ]
    }
]

FAKE_MEMORIES = [
    {
        "id": "memory-1",
        "uid": "test-user-id",                  # ✅ REQUIRED by mobile app
        "title": "Test Memory",
        "content": "This works without auth!",  # ✅ REQUIRED (was 'overview')
        "overview": "This works without auth!",
        "category": "interesting",              # ✅ Must match enum values
        "created_at": "2025-09-17T00:00:00Z",
        "updated_at": "2025-09-17T00:00:00Z"   # ✅ REQUIRED by mobile app
    }
]

@app.get("/")
def read_root():
    return {"message": "Taya Backend - No Auth Required!", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "port": os.environ.get("PORT", "8080")}

@app.get("/v1/health")
def health_check_v1():
    return {"status": "ok"}

@app.get("/v1/conversations")
def get_conversations():
    """Get conversations without authentication"""
    return FAKE_CONVERSATIONS

@app.post("/v1/conversations")
def create_conversation(data: dict):
    """Create conversation without authentication"""
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"

    new_conversation = {
        "id": f"test-{len(FAKE_CONVERSATIONS) + 1}",
        "title": data.get("title", "New Conversation"),
        "overview": data.get("overview", ""),
        "emoji": "🆕",
        "category": "user",
        "created_at": now,  # ✅ REQUIRED by mobile app
        "started_at": now,  # ✅ REQUIRED by mobile app
        "finished_at": now, # ✅ REQUIRED by mobile app
        "structured": {     # ✅ REQUIRED by mobile app
            "title": data.get("title", "New Conversation"),
            "overview": data.get("overview", ""),
            "emoji": "🆕",
            "category": "user",
            "action_items": data.get("action_items", []),
            "events": []
        },
        "transcript_segments": data.get("transcript_segments", []),
        "action_items": data.get("action_items", [])
    }
    FAKE_CONVERSATIONS.append(new_conversation)
    return new_conversation

@app.get("/v3/memories")
def get_memories():
    """Get memories without authentication"""
    return FAKE_MEMORIES

@app.post("/v3/memories")
def create_memory(memory: dict):
    """Create memory without authentication"""
    new_memory = {
        "id": f"memory-{len(FAKE_MEMORIES) + 1}",
        "title": memory.get("title", "Untitled"),
        "overview": memory.get("overview", ""),
        "category": memory.get("category", "other"),
        "created_at": "2025-09-17T00:00:00Z"
    }
    FAKE_MEMORIES.append(new_memory)
    return new_memory

@app.get("/v1/public-conversations")
def get_public_conversations():
    """Mock public conversations like Omi's backend"""
    return FAKE_CONVERSATIONS

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)