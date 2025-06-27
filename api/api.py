from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.generate_diagram import router as generate_diagram_router
from api.language_config import router as language_config_router
from api.processed_projects import router as processed_projects_router
from api.simple_chat import router as simple_chat_router
from api.websocket_wiki import handle_websocket_chat
from api.wiki import router as wiki_router
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
app.include_router(simple_chat_router)
app.include_router(language_config_router)
app.include_router(processed_projects_router)
app.include_router(wiki_router)
app.include_router(generate_diagram_router)
