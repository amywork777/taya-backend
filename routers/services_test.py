from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio
from utils.redis_client import redis_client
from utils.pinecone_client import pinecone_client

router = APIRouter(prefix="/services", tags=["services"])

@router.get("/health")
async def services_health():
    """Check the health of all external services"""
    health_status = {
        "redis": {
            "available": redis_client.is_available(),
            "status": "unknown"
        },
        "pinecone": {
            "available": pinecone_client.is_available(),
            "status": "unknown"
        }
    }

    # Test Redis connection
    if redis_client.is_available():
        try:
            redis_ping = redis_client.ping()
            health_status["redis"]["status"] = "healthy" if redis_ping else "unhealthy"
        except Exception as e:
            health_status["redis"]["status"] = f"error: {str(e)}"

    # Test Pinecone connection
    if pinecone_client.is_available():
        try:
            stats = pinecone_client.get_stats()
            health_status["pinecone"]["status"] = "healthy" if stats else "unhealthy"
            if stats:
                health_status["pinecone"]["stats"] = stats
        except Exception as e:
            health_status["pinecone"]["status"] = f"error: {str(e)}"

    return health_status

@router.post("/redis/test")
async def test_redis():
    """Test Redis operations"""
    if not redis_client.is_available():
        raise HTTPException(status_code=503, detail="Redis not available")

    test_key = "test:redis"
    test_value = {"message": "Hello Redis!", "timestamp": "2024-01-01"}

    try:
        # Test SET
        set_result = redis_client.set(test_key, test_value, expire=60)

        # Test GET
        get_result = redis_client.get(test_key)

        # Test EXISTS
        exists_result = redis_client.exists(test_key)

        # Test DELETE
        delete_result = redis_client.delete(test_key)

        return {
            "operations": {
                "set": set_result,
                "get": get_result,
                "exists": exists_result,
                "delete": delete_result
            },
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis test failed: {str(e)}")

@router.post("/pinecone/test")
async def test_pinecone():
    """Test Pinecone operations"""
    if not pinecone_client.is_available():
        raise HTTPException(status_code=503, detail="Pinecone not available")

    try:
        # Test vector (dummy embedding)
        test_vector = [0.1] * 1536  # 1536 dimensions for OpenAI embeddings
        test_id = "test-vector-123"
        test_metadata = {"text": "This is a test vector", "user_id": "test-user"}

        # Test UPSERT
        upsert_result = pinecone_client.upsert_vectors([{
            "id": test_id,
            "values": test_vector,
            "metadata": test_metadata
        }])

        # Small delay to allow indexing
        await asyncio.sleep(1)

        # Test QUERY
        query_results = pinecone_client.query_vectors(
            query_vector=test_vector,
            top_k=5,
            include_metadata=True
        )

        # Test DELETE
        delete_result = pinecone_client.delete_vectors([test_id])

        # Get stats
        stats = pinecone_client.get_stats()

        return {
            "operations": {
                "upsert": upsert_result,
                "query": {
                    "results_count": len(query_results),
                    "results": query_results[:2] if query_results else []  # Limit output
                },
                "delete": delete_result,
                "stats": stats
            },
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pinecone test failed: {str(e)}")

@router.post("/memory/test")
async def test_memory_operations():
    """Test memory storage and retrieval (combining both services)"""
    if not pinecone_client.is_available():
        raise HTTPException(status_code=503, detail="Pinecone not available")

    try:
        # Simulate storing and retrieving memories
        test_memories = [
            {
                "id": "mem-001",
                "text": "I had coffee with John this morning",
                "embedding": [0.1 + i*0.01 for i in range(1536)],
                "user_id": "user-123"
            },
            {
                "id": "mem-002",
                "text": "Meeting scheduled for next week",
                "embedding": [0.2 + i*0.01 for i in range(1536)],
                "user_id": "user-123"
            }
        ]

        # Store memories
        store_results = []
        for memory in test_memories:
            result = pinecone_client.upsert_memory(
                memory_id=memory["id"],
                embedding=memory["embedding"],
                text=memory["text"],
                user_id=memory["user_id"],
                metadata={"created": "2024-01-01"}
            )
            store_results.append(result)

        # Small delay for indexing
        await asyncio.sleep(1)

        # Search memories
        search_query = [0.15 + i*0.01 for i in range(1536)]  # Similar to first memory
        search_results = pinecone_client.search_memories(
            query_embedding=search_query,
            user_id="user-123",
            top_k=5
        )

        # Clean up
        cleanup_result = pinecone_client.delete_vectors([mem["id"] for mem in test_memories])

        return {
            "operations": {
                "store_memories": store_results,
                "search_results": {
                    "count": len(search_results),
                    "memories": search_results
                },
                "cleanup": cleanup_result
            },
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory test failed: {str(e)}")