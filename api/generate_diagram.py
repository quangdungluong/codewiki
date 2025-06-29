import asyncio
import json
import os
import re
import traceback
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models import DiagramCacheData, DiagramRequest
from api.services.gemini_service import GeminiService
from api.services.github_service import GithubService
from utils.constants import DIAGRAM_CACHE_DIR
from utils.logger import logger
from utils.prompts import SYSTEM_SECOND_PROMPT, SYSTEM_THIRD_PROMPT

router = APIRouter(prefix="/api/diagram")

gemini_service = GeminiService()


@lru_cache(maxsize=100)
def get_cached_github_data(owner: str, repo: str, token: Optional[str]):
    github_service = GithubService(owner=owner, repo=repo, token=token)
    file_tree, default_branch = github_service.get_tree_data()
    readme = github_service.get_readme()
    return {"file_tree": file_tree, "readme": readme, "default_branch": default_branch}


def process_click_events(diagram: str, owner: str, repo: str, branch: str) -> str:
    def replace_path(match):
        # Extract the path from the click event
        path = match.group(2).strip("\"'")

        # Determine if path is likely a file (has extension) or directory
        is_file = "." in path.split("/")[-1]

        # Construct GitHub URL
        base_url = f"https://github.com/{owner}/{repo}"
        path_type = "blob" if is_file else "tree"
        full_url = f"{base_url}/{path_type}/{branch}/{path}"

        # Return the full click event with the new URL
        return f'click {match.group(1)} "{full_url}"'

    click_pattern = r'click ([^\s"]+)\s+"([^"]+)"'
    return re.sub(click_pattern, replace_path, diagram)


def handle_mermaid_validation(diagram: str) -> str:
    # If the diagram is a JSON object, convert it to a string
    if diagram.startswith("{"):
        diagram = json.loads(diagram)
        diagram = list(diagram.values())[0]
    try:
        diagram = json.loads(diagram)
    except json.JSONDecodeError:
        pass
    # If the diagram include invalid mermaid syntax
    # Case 1: <--, [--., .->]
    diagram = (
        diagram.replace("<--", "-->")
        .replace("-->>", "-->")
        .replace("--.", "-->|")
        .replace(".->", "|")
    )
    # Case 2: Replace lines starting with optional whitespace followed by a single %
    diagram = re.sub(r"(^\s*)%(?!%)", r"\1%%", diagram, flags=re.MULTILINE)
    # Case 3: Replace \" inside node labels with single quotes or remove the escape
    diagram = re.sub(r'\[\s*"([^"]*?)\\\"([^"]*?)"\s*\]', r'["\1\'\2"]', diagram)
    # Case 4: Remove direction TD
    diagram = re.sub(r"direction TD", "", diagram)
    return diagram


def get_diagram_cache_path(owner: str, repo: str, repo_type: str) -> str:
    filename = f"{owner}_{repo}_{repo_type}_diagram_cache.txt"
    return os.path.join(DIAGRAM_CACHE_DIR, filename)


async def read_diagram_cache_data(
    owner: str, repo: str, repo_type: str
) -> Optional[str]:
    cache_path = get_diagram_cache_path(owner, repo, repo_type)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading diagram cache data: {e}")
            return None
    return None


async def write_diagram_cache_data(
    owner: str, repo: str, repo_type: str, data: str
) -> bool:
    cache_path = get_diagram_cache_path(owner, repo, repo_type)
    try:
        with open(cache_path, "w", encoding="utf-8") as file:
            file.write(data)
        return True
    except Exception as e:
        logger.error(f"Error writing diagram cache data: {e}")
        return False


@router.get("/cached")
async def get_cached_diagram(owner: str, repo: str):
    logger.info(f"Getting cached diagram for {owner}/{repo}")
    cached_diagram = await read_diagram_cache_data(owner, repo, "github")
    if cached_diagram:
        return {"diagram": cached_diagram}
    else:
        return None


@router.post("/cached")
async def cache_diagram(request: DiagramCacheData):
    logger.info(f"Caching diagram for {request.owner}/{request.repo}")
    success = await write_diagram_cache_data(
        request.owner, request.repo, "github", request.diagram
    )
    if success:
        return {"message": "Diagram cached successfully."}
    else:
        return {"message": "Failed to cache diagram."}


@router.post("/generate")
async def generate_diagram(request: DiagramRequest):
    try:

        async def generate_diagram_stream():
            try:
                github_data = get_cached_github_data(
                    owner=request.owner, repo=request.repo, token=request.token
                )
                file_tree = github_data["file_tree"]
                readme = github_data["readme"]
                default_branch = github_data["default_branch"]

                # Send initial message
                yield f"data: {json.dumps({'status': 'started', 'message': 'Generating diagram...'})}\n\n"
                await asyncio.sleep(0.1)

                # 1. Get explanation
                yield f"data: {json.dumps({'status': 'explanation', 'message': 'Generating explanation...'})}\n\n"
                await asyncio.sleep(0.1)

                explanation = ""
                async for chunk in gemini_service.generate(
                    system_prompt=SYSTEM_SECOND_PROMPT,
                    data={"file_tree": file_tree, "readme": readme},
                ):
                    explanation += chunk
                    yield f"data: {json.dumps({'status': 'explanation_chunk', 'chunk': chunk})}\n\n"

                # 2. Get component mapping
                yield f"data: {json.dumps({'status': 'mapping', 'message': 'Generating component mapping...'})}\n\n"
                await asyncio.sleep(0.1)
                component_mapping = ""
                async for chunk in gemini_service.generate(
                    system_prompt=SYSTEM_SECOND_PROMPT,
                    data={"explanation": explanation, "file_tree": file_tree},
                ):
                    component_mapping += chunk
                    yield f"data: {json.dumps({'status': 'mapping_chunk', 'chunk': chunk})}\n\n"

                # 3. Generate diagram
                yield f"data: {json.dumps({'status': 'diagram', 'message': 'Generating diagram...'})}\n\n"
                await asyncio.sleep(0.1)
                diagram = ""
                async for chunk in gemini_service.generate(
                    system_prompt=SYSTEM_THIRD_PROMPT,
                    data={
                        "explanation": explanation,
                        "component_mapping": component_mapping,
                    },
                ):
                    diagram += chunk
                    yield f"data: {json.dumps({'status': 'diagram_chunk', 'chunk': chunk})}\n\n"

                diagram = diagram.replace("```diagram", "").replace("```", "")
                processed_diagram = process_click_events(
                    diagram, request.owner, request.repo, default_branch
                )
                processed_diagram = handle_mermaid_validation(processed_diagram)
                logger.info(type(processed_diagram))
                logger.info(f"Processed diagram: {processed_diagram}")
                yield f"data: {json.dumps({'status': 'complete', 'diagram': processed_diagram, 'explanation': explanation, 'mapping': component_mapping, })}\n\n"

            except Exception as e:
                traceback.print_exc()
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate_diagram_stream(),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",  # Hint to Nginx
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
