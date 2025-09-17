import hashlib
import json
import os
import uuid
import base64

from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials

# Setup Google Cloud credentials from base64 if SERVICE_ACCOUNT_JSON is not provided
if not os.environ.get('SERVICE_ACCOUNT_JSON') and os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_BASE64'):
    try:
        credentials_base64 = os.environ['GOOGLE_APPLICATION_CREDENTIALS_BASE64']
        credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
        # Set SERVICE_ACCOUNT_JSON so existing code can use it
        os.environ['SERVICE_ACCOUNT_JSON'] = credentials_json
        print("✅ Google Cloud credentials set up from base64 in _client.py")
    except Exception as e:
        print(f"❌ Error setting up Google Cloud credentials from base64 in _client.py: {e}")
        raise

if os.environ.get('SERVICE_ACCOUNT_JSON'):
    service_account_info = json.loads(os.environ["SERVICE_ACCOUNT_JSON"])
    # Use the service account info directly
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
    db = firestore.Client.from_service_account_info(service_account_info)
else:
    db = firestore.Client()


def get_users_uid():
    users_ref = db.collection('users')
    return [str(doc.id) for doc in users_ref.stream()]


def document_id_from_seed(seed: str) -> uuid.UUID:
    """Avoid repeating the same data"""
    seed_hash = hashlib.sha256(seed.encode('utf-8')).digest()
    generated_uuid = uuid.UUID(bytes=seed_hash[:16], version=4)
    return str(generated_uuid)
