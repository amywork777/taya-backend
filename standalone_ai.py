"""
Standalone AI processing functions without database dependencies
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from dataclasses import dataclass
import os

# Simplified models without database dependencies
@dataclass
class ActionItem:
    description: str
    completed: bool = False

@dataclass
class Event:
    title: str
    description: str
    start: Optional[datetime] = None
    duration: Optional[int] = None

@dataclass
class Structured:
    title: Optional[str] = None
    overview: Optional[str] = None
    emoji: Optional[str] = None
    category: Optional[str] = None
    action_items: List[ActionItem] = None
    events: List[Event] = None

def should_discard_conversation(transcript: str) -> bool:
    """
    Simple heuristic to determine if a conversation should be discarded
    """
    if not transcript or len(transcript.strip()) < 10:
        return True

    # Check for meaningful content
    words = transcript.split()
    if len(words) < 3:
        return True

    # Check for test/placeholder content
    test_phrases = ["test", "testing", "hello world", "mock", "sample"]
    if any(phrase in transcript.lower() for phrase in test_phrases):
        return True

    return False

def get_transcript_structure(transcript: str, started_at: datetime, language_code: str = "en", tz: str = "UTC") -> Structured:
    """
    Simple AI processing to generate conversation structure
    In a real implementation, this would call OpenAI/LLM
    """
    try:
        # For now, create a basic structure
        # In production, this would use the actual LLM call

        # Extract potential action items (simple keyword detection)
        action_items = []
        action_keywords = ["todo", "task", "need to", "should", "must", "action", "follow up"]
        sentences = transcript.split('.')

        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in action_keywords):
                action_items.append(ActionItem(
                    description=sentence.strip(),
                    completed=False
                ))

        # Generate simple title and overview
        words = transcript.split()[:20]  # First 20 words
        title = f"Conversation on {started_at.strftime('%B %d')}"
        if len(words) > 5:
            title = f"Discussion about {' '.join(words[2:6])}"

        overview = transcript[:200] + "..." if len(transcript) > 200 else transcript

        return Structured(
            title=title,
            overview=overview,
            emoji="💬",
            category="general",
            action_items=action_items,
            events=[]
        )

    except Exception as e:
        print(f"AI processing error: {e}")
        # Fallback to basic structure
        return Structured(
            title="New Conversation",
            overview="AI processing unavailable",
            emoji="💬",
            category="general",
            action_items=[],
            events=[]
        )