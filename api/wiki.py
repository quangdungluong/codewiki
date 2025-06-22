import uuid
from http.client import HTTPException
from typing import Any

from fastapi import APIRouter, BackgroundTasks

from api.models import WikiTaskRequest, WikiTaskStatus
from utils.logger import logger
from utils.repository_structure import RepositoryStructureFetcher

router = APIRouter(prefix="/api/wiki", tags=["Wiki"])

tasks = {}  # replace with Redis


def update_task_status(
    task_id: str,
    status: str,
    message: str = "",
    result: Any = None,
    progress: set = set(),
):
    tasks[task_id]["status"] = status
    tasks[task_id]["message"] = message
    tasks[task_id]["result"] = result
    tasks[task_id]["progress"] = progress


@router.post("/generate")
async def generate_wiki(wiki: WikiTaskRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "started",
        "message": "Generating wiki...",
        "progress": set(),
        "error": None,
        "result": None,
    }
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
        # tasks[task_id]["status"] = "success"
        # tasks[task_id]["result"] = fetcher.wiki_structure
        # tasks[task_id]["message"] = "Wiki generated successfully"
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)


@router.get("/status/{task_id}", response_model=WikiTaskStatus)
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]
