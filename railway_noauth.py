import json
import os
import firebase_admin
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
import base64

# Import the AI processing functions we need
from utils.conversations.process_conversation import process_conversation, create_conversation_from_data
from utils.llm.conversation_processing import get_transcript_structure, should_discard_conversation
from models.conversation import CreateConversation, Conversation, ConversationStatus, ConversationSource
from models.memories import Memory

# Initialize Firebase for AI features
if not firebase_admin._apps:
    if os.environ.get('SERVICE_ACCOUNT_JSON'):
        service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
        credentials = firebase_admin.credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(credentials)
    elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_BASE64'):
        import base64
        service_account_info = json.loads(base64.b64decode(os.environ["GOOGLE_APPLICATION_CREDENTIALS_BASE64"]).decode())
        credentials = firebase_admin.credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(credentials)
    else:
        firebase_admin.initialize_app()

app = FastAPI(title="Taya Backend - AI Processing No Auth", version="1.0.0")

# Enable CORS for web/mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for testing (no database)
CONVERSATIONS_STORAGE = []
MEMORIES_STORAGE = []

# Mock user ID for all operations
MOCK_USER_ID = "test-user-no-auth"

@app.get("/")
def read_root():
    return {"message": "Taya Backend - AI Processing No Auth!", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "ai_enabled": True}

@app.get("/v1/health")
def health_check_v1():
    return {"status": "ok", "ai_enabled": True}

@app.get("/v1/conversations")
def get_conversations():
    """Get conversations with AI processing enabled"""
    return CONVERSATIONS_STORAGE

@app.post("/v1/conversations")
def create_conversation_with_ai(data: dict):
    """Create conversation with full AI processing (no auth required)"""
    try:
        # Extract transcript if provided
        transcript_text = ""
        transcript_segments = data.get("transcript_segments", [])

        if transcript_segments:
            # Combine all transcript segments into text
            transcript_text = " ".join([seg.get("text", "") for seg in transcript_segments])

        # If we have a transcript, process it with AI
        if transcript_text.strip():
            # Check if conversation should be discarded
            if should_discard_conversation(transcript_text):
                raise HTTPException(status_code=400, detail="Conversation content not meaningful enough to save")

            # Generate AI structure from transcript
            try:
                structured = get_transcript_structure(
                    transcript=transcript_text,
                    started_at=datetime.now(timezone.utc),
                    language_code="en",  # Default to English
                    tz="UTC"
                )

                # Create conversation with AI-generated structure
                new_conversation = {
                    "id": f"ai-conv-{len(CONVERSATIONS_STORAGE) + 1}",
                    "title": structured.title or data.get("title", "AI Generated Conversation"),
                    "overview": structured.overview or data.get("overview", ""),
                    "emoji": structured.emoji or "🤖",
                    "category": structured.category or "general",
                    "created_at": datetime.now(timezone.utc).isoformat() + "Z",
                    "started_at": datetime.now(timezone.utc).isoformat() + "Z",
                    "finished_at": datetime.now(timezone.utc).isoformat() + "Z",
                    "structured": {
                        "title": structured.title or data.get("title", "AI Generated"),
                        "overview": structured.overview or "",
                        "emoji": structured.emoji or "🤖",
                        "category": structured.category or "general",
                        "action_items": [
                            {"description": item.description, "completed": item.completed}
                            for item in (structured.action_items or [])
                        ],
                        "events": [
                            {
                                "title": event.title,
                                "description": event.description,
                                "start": event.start.isoformat() if event.start else None,
                                "duration": event.duration
                            }
                            for event in (structured.events or [])
                        ]
                    },
                    "transcript_segments": transcript_segments,
                    "action_items": [
                        {"description": item.description, "completed": item.completed}
                        for item in (structured.action_items or [])
                    ]
                }

            except Exception as ai_error:
                # If AI processing fails, fall back to basic creation
                print(f"AI processing failed: {ai_error}")
                new_conversation = {
                    "id": f"fallback-{len(CONVERSATIONS_STORAGE) + 1}",
                    "title": data.get("title", "New Conversation"),
                    "overview": data.get("overview", "AI processing unavailable"),
                    "emoji": "📝",
                    "category": "user",
                    "created_at": datetime.now(timezone.utc).isoformat() + "Z",
                    "started_at": datetime.now(timezone.utc).isoformat() + "Z",
                    "finished_at": datetime.now(timezone.utc).isoformat() + "Z",
                    "structured": {
                        "title": data.get("title", "New Conversation"),
                        "overview": data.get("overview", ""),
                        "emoji": "📝",
                        "category": "user",
                        "action_items": data.get("action_items", []),
                        "events": []
                    },
                    "transcript_segments": transcript_segments,
                    "action_items": data.get("action_items", [])
                }
        else:
            # No transcript provided, create basic conversation
            new_conversation = {
                "id": f"basic-{len(CONVERSATIONS_STORAGE) + 1}",
                "title": data.get("title", "New Conversation"),
                "overview": data.get("overview", ""),
                "emoji": "💬",
                "category": "user",
                "created_at": datetime.now(timezone.utc).isoformat() + "Z",
                "started_at": datetime.now(timezone.utc).isoformat() + "Z",
                "finished_at": datetime.now(timezone.utc).isoformat() + "Z",
                "structured": {
                    "title": data.get("title", "New Conversation"),
                    "overview": data.get("overview", ""),
                    "emoji": "💬",
                    "category": "user",
                    "action_items": data.get("action_items", []),
                    "events": []
                },
                "transcript_segments": transcript_segments,
                "action_items": data.get("action_items", [])
            }

        CONVERSATIONS_STORAGE.append(new_conversation)
        return new_conversation

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@app.get("/v3/memories")
def get_memories():
    """Get memories (no auth required)"""
    return MEMORIES_STORAGE

@app.post("/v3/memories")
def create_memory(memory: dict):
    """Create memory (no auth required)"""
    new_memory = {
        "id": f"memory-{len(MEMORIES_STORAGE) + 1}",
        "uid": MOCK_USER_ID,
        "title": memory.get("title", "Untitled"),
        "content": memory.get("content", memory.get("overview", "")),
        "overview": memory.get("overview", ""),
        "category": memory.get("category", "interesting"),
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "updated_at": datetime.now(timezone.utc).isoformat() + "Z"
    }
    MEMORIES_STORAGE.append(new_memory)
    return new_memory

@app.get("/v1/public-conversations")
def get_public_conversations():
    """Mock public conversations like Omi's backend"""
    return CONVERSATIONS_STORAGE

# TRANSCRIPTION ENDPOINTS

@app.websocket("/v4/listen")
async def websocket_transcribe(
    websocket: WebSocket,
    uid: str = "test-user",
    language: str = "en",
    sample_rate: int = 8000,
    codec: str = "pcm16",
    channels: int = 1,
    include_speech_profile: bool = False
):
    """
    Simplified transcription WebSocket for testing (no real STT)
    This is a mock endpoint that simulates transcription responses
    """
    await websocket.accept()

    try:
        # Send initial connection success
        await websocket.send_json({
            "type": "message_event",
            "event": "conversation_started",
            "data": {
                "conversation_id": f"mock-{datetime.now().timestamp()}",
                "session_id": f"session-{datetime.now().timestamp()}"
            }
        })

        segment_counter = 0

        while True:
            try:
                # Receive audio data
                data = await websocket.receive()

                if data["type"] == "websocket.receive":
                    if "bytes" in data:
                        # Mock transcription response after receiving audio
                        segment_counter += 1

                        # Send mock transcript segment
                        mock_segment = {
                            "type": "message_event",
                            "event": "segment_received",
                            "data": {
                                "segment": {
                                    "text": f"Mock transcribed audio segment {segment_counter}",
                                    "speaker": "SPEAKER_0",
                                    "speaker_id": 0,
                                    "is_user": True,
                                    "start": segment_counter * 2.0,
                                    "end": (segment_counter * 2.0) + 1.8,
                                    "confidence": 0.95
                                },
                                "session_id": f"session-{datetime.now().timestamp()}"
                            }
                        }

                        await websocket.send_json(mock_segment)

                    elif "text" in data:
                        # Handle text messages (like heartbeat)
                        message = data["text"]
                        if message == "heartbeat":
                            await websocket.send_json({
                                "type": "message_event",
                                "event": "heartbeat_ack",
                                "data": {}
                            })

            except asyncio.TimeoutError:
                # Send heartbeat if no data received
                await websocket.send_json({
                    "type": "message_event",
                    "event": "heartbeat",
                    "data": {}
                })

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

@app.post("/v1/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Simple audio file transcription endpoint (mock for testing)
    In production, this would use Deepgram/Whisper/etc.
    """
    try:
        # Read the uploaded audio file
        audio_content = await file.read()

        # Mock transcription result
        mock_transcript = [
            {
                "text": "This is a mock transcription of your audio file.",
                "speaker": "SPEAKER_0",
                "speaker_id": 0,
                "start": 0.0,
                "end": 3.0,
                "confidence": 0.95
            },
            {
                "text": "The AI processing will work on this mock transcript.",
                "speaker": "SPEAKER_0",
                "speaker_id": 0,
                "start": 3.0,
                "end": 6.0,
                "confidence": 0.92
            }
        ]

        return {
            "success": True,
            "transcript": mock_transcript,
            "language": "en",
            "duration": 6.0,
            "note": "This is a mock transcription for testing. Real STT requires audio processing setup."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# Create necessary directories
paths = ['_temp', '_samples', '_segments', '_speech_profiles']
for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))