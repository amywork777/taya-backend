from fastapi import APIRouter
from utils.redis_client import redis_client
from utils.pinecone_client import pinecone_client

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/redis")
async def test_redis_simple():
    """Simple Redis test"""
    if not redis_client.is_available():
        return {"status": "Redis not configured"}

    try:
        # Test basic ping
        ping_result = redis_client.ping()
        return {
            "redis_available": True,
            "ping_result": ping_result,
            "status": "healthy" if ping_result else "unhealthy"
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}

@router.get("/pinecone")
async def test_pinecone_simple():
    """Simple Pinecone test"""
    if not pinecone_client.is_available():
        return {"status": "Pinecone not configured"}

    try:
        # Test getting stats
        stats = pinecone_client.get_stats()
        return {
            "pinecone_available": True,
            "stats": stats,
            "status": "healthy" if stats else "unhealthy"
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}

@router.get("/all")
async def test_all_simple():
    """Test all services simply"""
    results = {
        "redis": {"available": redis_client.is_available()},
        "pinecone": {"available": pinecone_client.is_available()}
    }

    if redis_client.is_available():
        try:
            results["redis"]["ping"] = redis_client.ping()
        except Exception as e:
            results["redis"]["error"] = str(e)

    if pinecone_client.is_available():
        try:
            stats = pinecone_client.get_stats()
            results["pinecone"]["has_stats"] = stats is not None
        except Exception as e:
            results["pinecone"]["error"] = str(e)

    return results