import redis
import os
import hashlib
import json

def get_redis_client():
    '''Get Redis client (fallback to None if unavailable)'''
    try:
        client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        client.ping()
        return client
    except:
        return None

def get_cache_key(code: str) -> str:
    '''Generate cache key from code hash'''
    return f'analysis:{hashlib.sha256(code.encode()).hexdigest()}'

def get_cached_analysis(code: str):
    '''Get cached analysis if exists'''
    client = get_redis_client()
    if not client:
        return None
    
    key = get_cache_key(code)
    cached = client.get(key)
    return json.loads(cached) if cached else None

def set_cached_analysis(code: str, result: dict, ttl: int = 86400):
    '''Cache analysis result'''
    client = get_redis_client()
    if not client:
        return
    
    key = get_cache_key(code)
    client.setex(key, ttl, json.dumps(result))
