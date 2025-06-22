import os

MAX_EMBEDDING_TOKEN = 8192
TARGET_SERVER_BASE_URL = "http://localhost:8001"

WIKI_CACHE_DIR = os.path.join("./.cache", "wiki_cache")
os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
