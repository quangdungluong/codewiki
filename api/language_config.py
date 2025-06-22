from fastapi import APIRouter

from api.config import configs

router = APIRouter(prefix="/lang/config", tags=["Language Configuration"])


@router.get("")
async def get_language_config():
    return configs["language_config"]
