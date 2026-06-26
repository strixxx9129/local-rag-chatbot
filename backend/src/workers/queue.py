# backend/src/workers/queue.py
import redis
from rq import Queue

from src.core.config import settings

redis_conn = redis.from_url(settings.redis_url, decode_responses=False)

document_queue = Queue(
    name="documents",
    connection=redis_conn,
    default_timeout=1800,
)

memory_queue = Queue(            # ← ADD
    name="memory",
    connection=redis_conn,
    default_timeout=300,         # 5 minutes max per summarization
)