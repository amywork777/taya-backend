#!/usr/bin/env python3
"""
Comprehensive Omi Backend Setup Status Check
Based on: https://docs.omi.me/doc/developer/backend/Backend_Setup
"""

import os
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

def check_command(cmd):
    """Check if a command is available"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def get_env_status(key):
    """Check environment variable status"""
    value = os.getenv(key)
    if not value:
        return "❌ Missing"
    elif value and len(value) > 20:
        return "✅ Set"
    elif value:
        return "⚠️ Set (short)"
    return "❌ Missing"

def main():
    print("🎯 COMPREHENSIVE TAYA BACKEND STATUS")
    print("=" * 50)

    print("\n📋 CORE REQUIREMENTS:")
    requirements = {
        "Python": check_command("python3 --version"),
        "pip": check_command("pip --version"),
        "Git": check_command("git --version"),
        "FFmpeg": check_command("ffmpeg -version"),
        "Google Cloud SDK": check_command("gcloud --version"),
        "Ngrok": check_command("ngrok version"),
    }

    for req, status in requirements.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {req}")

    print("\n🔑 REQUIRED API KEYS:")
    api_keys = {
        "OpenAI": "OPENAI_API_KEY",
        "Deepgram": "DEEPGRAM_API_KEY",
        "Redis (Upstash)": "UPSTASH_REDIS_REST_TOKEN",
        "Pinecone": "PINECONE_API_KEY",
        "Google OAuth ID": "GOOGLE_CLIENT_ID",
        "Google OAuth Secret": "GOOGLE_CLIENT_SECRET",
        "Google Credentials": "GOOGLE_APPLICATION_CREDENTIALS"
    }

    for service, env_var in api_keys.items():
        status = get_env_status(env_var)
        print(f"   {status} {service}")

    print("\n🛠️ OPTIONAL SERVICES:")
    optional_keys = {
        "HuggingFace Token": "HUGGINGFACE_TOKEN",
        "Modal Token": "MODAL_TOKEN_ID",
        "GitHub Token": "GITHUB_TOKEN",
        "Google Maps": "GOOGLE_MAPS_API_KEY",
        "Typesense": "TYPESENSE_API_KEY",
        "Stripe": "STRIPE_SECRET_KEY"
    }

    for service, env_var in optional_keys.items():
        status = get_env_status(env_var)
        print(f"   {status} {service}")

    print("\n🏗️ INFRASTRUCTURE STATUS:")
    try:
        import requests
        # Test local server
        try:
            resp = requests.get("http://localhost:8080/", timeout=2)
            server_status = "✅ Running" if resp.status_code == 200 else "❌ Error"
        except:
            server_status = "❌ Not running"

        # Test Redis
        try:
            resp = requests.get("http://localhost:8080/test/redis", timeout=2)
            redis_status = "✅ Working" if resp.status_code == 200 else "❌ Error"
        except:
            redis_status = "❌ Cannot test"

        # Test Pinecone
        try:
            resp = requests.get("http://localhost:8080/test/pinecone", timeout=2)
            pinecone_status = "✅ Working" if resp.status_code == 200 else "❌ Error"
        except:
            pinecone_status = "❌ Cannot test"

        # Test OAuth
        try:
            resp = requests.get("http://localhost:8080/auth/status", timeout=2)
            oauth_status = "✅ Configured" if "configured\":true" in resp.text else "❌ Not configured"
        except:
            oauth_status = "❌ Cannot test"

    except ImportError:
        server_status = redis_status = pinecone_status = oauth_status = "❓ Cannot test (requests not installed)"

    print(f"   {server_status} FastAPI Server")
    print(f"   {redis_status} Redis Connection")
    print(f"   {pinecone_status} Pinecone Connection")
    print(f"   {oauth_status} OAuth System")

    print("\n🎯 COMPLETION STATUS:")
    required_count = sum(1 for status in requirements.values() if status)
    required_total = len(requirements)

    api_count = sum(1 for env_var in api_keys.values() if os.getenv(env_var))
    api_total = len(api_keys)

    print(f"   Core Requirements: {required_count}/{required_total}")
    print(f"   Required API Keys: {api_count}/{api_total}")

    if required_count == required_total and api_count >= 6:  # Core + most important APIs
        print("\n🎉 BACKEND IS PRODUCTION READY! 🚀")
    elif required_count == required_total:
        print("\n⚠️  BACKEND IS FUNCTIONAL - Some API keys missing")
    else:
        print("\n❌ SETUP INCOMPLETE - Core requirements missing")

    print("\n📚 Next Steps:")
    if api_count < api_total:
        print("   • Add missing API keys to .env file")
    print("   • Test all endpoints with curl commands")
    print("   • Build your first AI application!")

if __name__ == "__main__":
    main()