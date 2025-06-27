import json
import re
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models import DiagramRequest
from api.services.gemini_service import GeminiService
from api.services.github_service import GithubService
from utils.prompts import SYSTEM_SECOND_PROMPT, SYSTEM_THIRD_PROMPT

router = APIRouter(prefix="/diagram")

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

                # 1. Get explanation
                yield f"data: {json.dumps({'status': 'generating_explanation', 'message': 'Generating explanation...'})}\n\n"
                explanation = ""
                async for chunk in gemini_service.generate(
                    system_prompt=SYSTEM_SECOND_PROMPT,
                    data={"file_tree": file_tree, "readme": readme},
                ):
                    explanation += chunk
                    yield f"data: {json.dumps({'status': 'explanation_chunk', 'chunk': chunk})}\n\n"

                # 2. Get component mapping
                yield f"data: {json.dumps({'status': 'generating_component_mapping', 'message': 'Generating component mapping...'})}\n\n"
                component_mapping = ""
                async for chunk in gemini_service.generate(
                    system_prompt=SYSTEM_SECOND_PROMPT,
                    data={"explanation": explanation, "file_tree": file_tree},
                ):
                    component_mapping += chunk
                    yield f"data: {json.dumps({'status': 'component_mapping_chunk', 'chunk': chunk})}\n\n"

                # 3. Generate diagram
                yield f"data: {json.dumps({'status': 'generating_diagram', 'message': 'Generating diagram...'})}\n\n"
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

                yield f"data: {json.dumps({'status': 'complete', 'diagram': processed_diagram, 'explanation': explanation, 'mapping': component_mapping, })}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate_diagram_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
