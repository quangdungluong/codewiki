import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from api.models import WikiCacheData, WikiCacheRequest
from utils.constants import WIKI_CACHE_DIR
from utils.logger import logger

router = APIRouter(prefix="/api/wiki_cache", tags=["Wiki Cache"])


def get_wiki_cache_path(owner: str, repo: str, repo_type: str) -> str:
    filename = f"{owner}_{repo}_{repo_type}_wiki_cache.json"
    return os.path.join(WIKI_CACHE_DIR, filename)


async def read_wiki_cache_data(
    owner: str, repo: str, repo_type: str
) -> Optional[WikiCacheData]:
    """
    Simulated function to read wiki cache data.
    In a real application, this would fetch data from a database or cache.
    """
    # This is a placeholder for actual data retrieval logic
    cache_path = get_wiki_cache_path(owner, repo, repo_type)
    logger.info(f"Reading wiki cache data from {cache_path}")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                # Here you would typically deserialize the JSON data into a WikiCacheData object
                return WikiCacheData(**data)  # Assuming the data is in JSON format
        except Exception as e:
            logger.error(f"Error reading wiki cache data: {e}")
            return None
    return None


async def write_wiki_cache_data(data: WikiCacheRequest) -> bool:
    cache_path = get_wiki_cache_path(data.owner, data.repo, data.repo_type)
    try:
        payload = WikiCacheData(
            wiki_structure=data.wiki_structure, generated_pages=data.generated_pages
        )
        with open(cache_path, "w", encoding="utf-8") as file:
            json.dump(payload.model_dump(), file, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error writing wiki cache data: {e}")
        return False


@router.get("", response_model=Optional[WikiCacheData])
async def get_wiki_cache(
    owner: str, repo: str, repo_type: str
) -> Optional[WikiCacheData]:
    """
    Retrieve the wiki cache data for a specific repository.
    """
    logger.info(f"Fetching wiki cache for {owner}/{repo} of type {repo_type}")
    cached_data = await read_wiki_cache_data(owner, repo, repo_type)
    if cached_data:
        return cached_data
    else:
        return None


@router.post("")
async def update_wiki_cache(request_data: WikiCacheRequest) -> Dict[str, Any]:
    """
    Update the wiki cache data for a specific repository.
    """
    logger.info(f"Updating wiki cache for {request_data.owner}/{request_data.repo}")

    success = await write_wiki_cache_data(request_data)

    if success:
        return {"message": "Wiki cache updated successfully."}
    else:
        return HTTPException(status_code=500, detail="Failed to update wiki cache.")
