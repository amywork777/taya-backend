import hashlib
import json
import os
import uuid

# If Supabase is configured, use the Supabase adapter and avoid Firebase entirely
if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
    from database.supabase_client import db  # type: ignore
else:
    # IMPORTANT: Ensure credentials are set up before any Google Cloud imports
    import setup_credentials  # noqa: F401

    from google.cloud import firestore
    import firebase_admin
    from firebase_admin import credentials

    if os.environ.get('SERVICE_ACCOUNT_JSON'):
        service_account_raw = os.environ.get("SERVICE_ACCOUNT_JSON", "")
        try:
            service_account_info = json.loads(service_account_raw)
        except Exception:
            service_account_info = None

        if service_account_info:
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
            db = firestore.Client.from_service_account_info(service_account_info)
        else:
            # Fallback to default client if env var is set but invalid
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            db = firestore.Client()
    else:
        # Default Firestore client
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        db = firestore.Client()


def get_users_uid():
    users_ref = db.collection('users')
    return [str(doc.id) for doc in users_ref.stream()]


def document_id_from_seed(seed: str) -> uuid.UUID:
    """Avoid repeating the same data"""
    seed_hash = hashlib.sha256(seed.encode('utf-8')).digest()
    generated_uuid = uuid.UUID(bytes=seed_hash[:16], version=4)
    return str(generated_uuid)
