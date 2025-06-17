from fastapi import FastAPI, WebSocket
from utils.logger import logger
from fastapi.middleware.cors import CORSMiddleware
from api.websocket_wiki import handle_websocket_chat
from api.wiki_cache import router as wiki_cache_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

app.add_websocket_route("/ws/chat", handle_websocket_chat)
app.include_router(wiki_cache_router)
