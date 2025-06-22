import asyncio
import os
from typing import List

from fastapi import APIRouter, HTTPException

from api.models import ProcessedProjectEntry
from utils.constants import WIKI_CACHE_DIR
from utils.logger import logger

router = APIRouter(prefix="/api/processed_projects", tags=["Processed Projects"])


@router.get("", response_model=List[ProcessedProjectEntry])
async def get_processed_projects():
    project_entries: List[ProcessedProjectEntry] = []
    try:
        filenames = await asyncio.to_thread(os.listdir, WIKI_CACHE_DIR)
        for filename in filenames:
            if filename.endswith("_wiki_cache.json"):
                file_path = os.path.join(WIKI_CACHE_DIR, filename)
                stats = await asyncio.to_thread(os.stat, file_path)
                parts = filename.replace("_wiki_cache.json", "").split("_")
                if len(parts) == 3:
                    owner, repo, repo_type = parts
                    project_entries.append(
                        ProcessedProjectEntry(
                            id=f"{filename}",
                            owner=owner,
                            repo=repo,
                            name=f"{owner}/{repo}",
                            repo_type=repo_type,
                            submitted_at=int(stats.st_mtime * 1000),
                            language="en",
                        )
                    )

        project_entries.sort(key=lambda x: x.submitted_at, reverse=True)
        return project_entries
    except Exception as e:
        logger.error(f"Error getting processed projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))
