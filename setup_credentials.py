"""
Credential setup utility that must be imported before any Google Cloud services.
This ensures credentials are available before Firebase/Firestore initialization.
"""

import os
import base64
import json


def setup_google_cloud_credentials():
    """
    Sets up Google Cloud credentials from base64 environment variable.
    Should be called before any Google Cloud service initialization.
    """
    if os.environ.get('SERVICE_ACCOUNT_JSON'):
        print("✅ SERVICE_ACCOUNT_JSON already set")
        return True

    if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_BASE64'):
        print("⚠️  No Google Cloud credentials found")
        return False

    try:
        print("🔧 Setting up Google Cloud credentials from base64...")
        credentials_base64 = os.environ['GOOGLE_APPLICATION_CREDENTIALS_BASE64']
        credentials_json = base64.b64decode(credentials_base64).decode('utf-8')

        # Validate JSON
        parsed = json.loads(credentials_json)
        if 'project_id' not in parsed:
            raise ValueError("Invalid service account JSON - missing project_id")

        # Set both environment variables for different auth methods
        os.environ['SERVICE_ACCOUNT_JSON'] = credentials_json

        # Also write to file for GOOGLE_APPLICATION_CREDENTIALS method
        os.makedirs('/tmp', exist_ok=True)
        with open('/tmp/service-account.json', 'w') as f:
            f.write(credentials_json)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/tmp/service-account.json'

        print(f"✅ Google Cloud credentials set up for project: {parsed['project_id']}")
        return True

    except Exception as e:
        print(f"❌ Error setting up Google Cloud credentials: {e}")
        raise


# Call immediately when module is imported
setup_google_cloud_credentials()