import json
import os
import firebase_admin
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
import base64
from deepgram import DeepgramClient, DeepgramClientOptions, LiveTranscriptionEvents
from deepgram.clients.live.v1 import LiveOptions

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
    return {"message": "Taya Backend - AI Processing No Auth (v2)!", "status": "healthy"}

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

# TRANSCRIPTION ENDPOINTS - Real Deepgram Integration

# Import STT functionality
from utils.stt.streaming import get_stt_service_for_language, STTService, process_audio_dg

# Initialize Deepgram client
deepgram_options = DeepgramClientOptions(options={"keepalive": "true", "termination_exception_connect": "true"})
deepgram = DeepgramClient(os.getenv('DEEPGRAM_API_KEY'), deepgram_options)

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
    Real-time transcription WebSocket using Deepgram (no auth required)
    """
    await websocket.accept()

    # Track segments for this session
    session_id = f"session-{datetime.now().timestamp()}"
    conversation_id = f"conv-{datetime.now().timestamp()}"

    try:
        # Send initial connection success
        await websocket.send_json({
            "type": "message_event",
            "event": "conversation_started",
            "data": {
                "conversation_id": conversation_id,
                "session_id": session_id
            }
        })

        # Get STT service and model for language
        stt_service, stt_language, model = get_stt_service_for_language(language)
        print(f"Using {stt_service} with language {stt_language} and model {model}")

        # Stream transcript callback
        def stream_transcript(segments):
            for segment in segments:
                # Send segment to client
                asyncio.create_task(websocket.send_json({
                    "type": "message_event",
                    "event": "segment_received",
                    "data": {
                        "segment": {
                            "text": segment["text"],
                            "speaker": segment["speaker"],
                            "speaker_id": int(segment["speaker"].split("_")[-1]) if "_" in segment["speaker"] else 0,
                            "is_user": segment["is_user"],
                            "start": segment["start"],
                            "end": segment["end"],
                            "confidence": 0.95  # Default confidence
                        },
                        "session_id": session_id
                    }
                }))

        # Initialize STT connection based on service
        if stt_service == STTService.deepgram:
            stt_socket = await process_audio_dg(
                stream_transcript=stream_transcript,
                language=stt_language,
                sample_rate=sample_rate,
                channels=channels,
                model=model
            )
        else:
            # Fallback to Deepgram if other services not available
            stt_socket = await process_audio_dg(
                stream_transcript=stream_transcript,
                language="en",
                sample_rate=sample_rate,
                channels=channels,
                model="nova-2-general"
            )

        # Audio processing loop
        while True:
            try:
                # Receive audio data from client
                data = await websocket.receive()

                if data["type"] == "websocket.receive":
                    if "bytes" in data:
                        # Send audio data to STT service
                        audio_data = data["bytes"]
                        if stt_socket and hasattr(stt_socket, 'send'):
                            stt_socket.send(audio_data)

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
        if 'stt_socket' in locals() and stt_socket:
            try:
                stt_socket.finish()
            except:
                pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
        if 'stt_socket' in locals() and stt_socket:
            try:
                stt_socket.finish()
            except:
                pass

@app.post("/v1/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Audio file transcription endpoint using Deepgram (no auth required)
    """
    try:
        # Read the uploaded audio file
        audio_content = await file.read()

        # Use Deepgram for file transcription
        if not os.getenv('DEEPGRAM_API_KEY'):
            raise HTTPException(status_code=500, detail="Deepgram API key not configured")

        # Initialize Deepgram client for file transcription
        dg_client = deepgram.listen.prerecorded.v("1")

        # Transcription options
        options = {
            "model": "nova-2-general",
            "language": "en",
            "smart_format": True,
            "diarize": True,
            "punctuate": True,
            "paragraphs": True,
        }

        # Call Deepgram API
        response = dg_client.transcribe_file(
            source={"buffer": audio_content},
            options=options
        )

        # Extract transcript segments
        transcript_segments = []
        if response.results and response.results.channels:
            channel = response.results.channels[0]
            if channel.alternatives:
                alternative = channel.alternatives[0]

                # Process paragraphs if available
                if hasattr(alternative, 'paragraphs') and alternative.paragraphs:
                    for paragraph in alternative.paragraphs.paragraphs:
                        for sentence in paragraph.sentences:
                            transcript_segments.append({
                                "text": sentence.text,
                                "speaker": f"SPEAKER_{sentence.speaker if hasattr(sentence, 'speaker') else 0}",
                                "speaker_id": sentence.speaker if hasattr(sentence, 'speaker') else 0,
                                "start": sentence.start,
                                "end": sentence.end,
                                "confidence": sentence.confidence if hasattr(sentence, 'confidence') else 0.95
                            })
                # Fallback to words if paragraphs not available
                elif hasattr(alternative, 'words') and alternative.words:
                    current_segment = None
                    for word in alternative.words:
                        speaker_id = word.speaker if hasattr(word, 'speaker') else 0

                        if current_segment is None or current_segment["speaker_id"] != speaker_id:
                            if current_segment:
                                transcript_segments.append(current_segment)
                            current_segment = {
                                "text": word.punctuated_word,
                                "speaker": f"SPEAKER_{speaker_id}",
                                "speaker_id": speaker_id,
                                "start": word.start,
                                "end": word.end,
                                "confidence": word.confidence if hasattr(word, 'confidence') else 0.95
                            }
                        else:
                            current_segment["text"] += f" {word.punctuated_word}"
                            current_segment["end"] = word.end

                    if current_segment:
                        transcript_segments.append(current_segment)

        return {
            "success": True,
            "transcript": transcript_segments,
            "language": "en",
            "duration": response.results.summary.total_time if response.results and hasattr(response.results, 'summary') else 0.0,
            "note": "Transcribed using Deepgram API"
        }

    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# Create necessary directories
paths = ['_temp', '_samples', '_segments', '_speech_profiles']
for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))