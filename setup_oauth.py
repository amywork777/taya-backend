#!/usr/bin/env python3
"""
OAuth Setup Helper Script
Run this to verify your Google OAuth setup step by step
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_oauth_setup():
    print("🔐 GOOGLE OAUTH SETUP CHECKER\n")

    # Check environment variables
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    print("📋 Current Configuration:")
    print(f"   Client ID: {'✅ Set' if client_id else '❌ Missing'}")
    print(f"   Client Secret: {'✅ Set' if client_secret else '❌ Missing'}")
    print(f"   Redirect URI: {redirect_uri or '❌ Missing'}")
    print()

    if not client_id or not client_secret:
        print("🚨 MISSING CREDENTIALS!")
        print("\n📝 TO FIX THIS:")
        print("1. Go to: https://console.cloud.google.com/apis/credentials")
        print("2. Select 'taya-backend' project")
        print("3. Click 'Create Credentials' → 'OAuth 2.0 Client IDs'")
        print("4. Choose 'Web application'")
        print("5. Add these redirect URIs:")
        print(f"   - http://localhost:8080/auth/google/callback")
        print(f"   - https://6060ceae9a02.ngrok-free.app/auth/google/callback")
        print("\n6. Copy the credentials and update your .env file:")
        print("   GOOGLE_CLIENT_ID=your_client_id_here")
        print("   GOOGLE_CLIENT_SECRET=your_client_secret_here")
        return False

    print("✅ OAuth credentials are configured!")
    print("\n🧪 TEST YOUR SETUP:")
    print("   1. curl http://localhost:8080/auth/status")
    print("   2. curl http://localhost:8080/auth/google/login")
    print("   3. Visit the authorization URL from step 2")

    return True

def create_oauth_links():
    """Generate the exact Google Cloud Console links you need"""
    project_id = "taya-backend"

    print("\n🔗 DIRECT LINKS TO SET UP OAUTH:")
    print(f"1. APIs & Services: https://console.cloud.google.com/apis/dashboard?project={project_id}")
    print(f"2. OAuth Consent Screen: https://console.cloud.google.com/apis/credentials/consent?project={project_id}")
    print(f"3. Create Credentials: https://console.cloud.google.com/apis/credentials?project={project_id}")
    print()

if __name__ == "__main__":
    create_oauth_links()
    check_oauth_setup()