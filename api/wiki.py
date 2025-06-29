import uuid
from http.client import HTTPException
from typing import Any

from fastapi import APIRouter, BackgroundTasks

from api.models import WikiTaskRequest, WikiTaskStatus
from utils.logger import logger
from utils.redis_tasks import RedisTasks
from utils.repository_structure import RepositoryStructureFetcher

router = APIRouter(prefix="/api/wiki", tags=["Wiki"])


def update_task_status(
    task_id: str,
    status: str,
    message: str = "",
    result: Any = None,
    progress: list[str] = [],
):
    RedisTasks().update_task(
        task_id,
        {
            "status": status,
            "message": message,
            "result": result.model_dump() if result is not None else result,
            "progress": progress,
        },
    )


@router.post("/generate")
async def generate_wiki(wiki: WikiTaskRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    RedisTasks().add_task(
        task_id,
        {
            "status": "started",
            "message": "Generating wiki...",
            "progress": [],
            "error": None,
            "result": None,
        },
    )

    background_tasks.add_task(generate_wiki, wiki, task_id)
    return {"task_id": task_id}


async def generate_wiki(wiki: WikiTaskRequest, task_id: str):
    try:
        fetcher = RepositoryStructureFetcher(
            repo_info=wiki.repo_info,
            repo_url=wiki.repo_url,
            owner=wiki.owner,
            repo=wiki.repo,
            token=wiki.token,
        )
        await fetcher.fetch_repository_structure(update_task_status, task_id)
    except Exception as e:
        RedisTasks().update_task(task_id, {"status": "error", "error": str(e)})


@router.get("/status/{task_id}", response_model=WikiTaskStatus)
async def get_task_status(task_id: str):
    task = RedisTasks().get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
