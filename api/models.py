from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatCompletionRequest(BaseModel):
    """
    Model for requesting a chat completion.
    """

    repo_url: str = Field(..., description="URL of the repository to query")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    filePath: Optional[str] = Field(
        None,
        description="Optional path to a file in the repository to include in the prompt",
    )
    token: Optional[str] = Field(
        None, description="Personal access token for private repositories"
    )
    type: Optional[str] = Field(
        "github",
        description="Type of repository (e.g., 'github', 'gitlab', 'bitbucket')",
    )

    # model parameters
    provider: str = Field(
        "google", description="Model provider (google, openai, openrouter, ollama)"
    )
    model: Optional[str] = Field(
        None, description="Model name for the specified provider"
    )

    language: Optional[str] = Field(
        "en",
        description="Language for content generation (e.g., 'en', 'ja', 'zh', 'es', 'kr', 'vi')",
    )
    excluded_dirs: Optional[str] = Field(
        None,
        description="Comma-separated list of directories to exclude from processing",
    )
    excluded_files: Optional[str] = Field(
        None,
        description="Comma-separated list of file patterns to exclude from processing",
    )
    included_dirs: Optional[str] = Field(
        None, description="Comma-separated list of directories to include exclusively"
    )
    included_files: Optional[str] = Field(
        None, description="Comma-separated list of file patterns to include exclusively"
    )


class WikiPage(BaseModel):
    """
    Model for a wiki page.
    """

    id: str
    title: str
    description: str
    content: str
    file_paths: List[str]
    importance: str
    related_pages: List[str]

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class WikiStructureModel(BaseModel):
    """
    Model for the wiki structure.
    """

    id: str
    title: str
    description: str
    pages: List[WikiPage]


class WikiCacheData(BaseModel):
    """
    Model for the wiki cache data.
    """

    wiki_structure: WikiStructureModel
    generated_pages: Dict[str, WikiPage]


class WikiCacheRequest(BaseModel):
    """
    Model for requesting wiki cache data.
    """

    owner: str
    repo: str
    repo_type: str
    wiki_structure: WikiStructureModel
    generated_pages: Dict[str, WikiPage]


class ProcessedProjectEntry(BaseModel):
    id: str
    owner: str
    repo: str
    name: str
    repo_type: str
    submitted_at: int  # timestampt
    language: str


class WikiTaskRequest(BaseModel):
    owner: str
    repo: str
    repo_url: str
    repo_info: Dict[str, Any]
    token: Optional[str] = None


class WikiTaskStatus(BaseModel):
    status: str
    message: str = ""
    progress: Optional[set[str]] = None
    error: Optional[str] = None
    result: Optional[WikiCacheData] = None
