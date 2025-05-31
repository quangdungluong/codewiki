import os
import re
from typing import Any, Dict, Optional, Union

from utils.logger import logger


def extract_url_path(url: str) -> Optional[str]:
    """Extract the path component from a URL."""
    if not url:
        return None

    # Remove protocol and domain
    parts = url.split("://")
    if len(parts) > 1:
        url = parts[1]

    # Get path after domain
    parts = url.split("/", 1)
    if len(parts) > 1:
        return parts[1]

    return None


def parse_repository_input(input_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse repository input string to extract owner, repo, type, and paths.

    Args:
        input_str: A string representing a repository path or URL

    Returns:
        A dictionary with owner, repo, type, and optional fullPath/localPath,
        or None if parsing fails
    """
    input_str = input_str.strip()

    owner = ""
    repo = ""
    repo_type = "github"
    full_path = None
    local_path = None

    # Handle Windows absolute paths (e.g., C:\path\to\folder)
    windows_path_regex = r'^[a-zA-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*$'
    custom_git_regex = r"^(?:https?:\/\/)?([^\/]+)\/(.+?)\/([^\/]+)(?:\.git)?\/?$"

    if re.match(windows_path_regex, input_str):
        repo_type = "local"
        local_path = input_str
        repo = os.path.basename(input_str) or "local-repo"
        owner = "local"

    # Handle Unix/Linux absolute paths (e.g., /path/to/folder)
    elif input_str.startswith("/"):
        repo_type = "local"
        local_path = input_str
        parts = [part for part in input_str.split("/") if part]
        repo = parts[-1] if parts else "local-repo"
        owner = "local"

    elif re.match(custom_git_regex, input_str):
        repo_type = "web"
        full_path = extract_url_path(input_str)
        if full_path:
            full_path = full_path.rstrip(".git")
            parts = full_path.split("/")
            if len(parts) >= 2:
                repo = parts[-1] or ""
                owner = parts[-2] or ""

    # Unsupported URL formats
    else:
        print(f"Unsupported URL format: {input_str}")
        return None

    if not owner or not repo:
        return None

    # Clean values
    owner = owner.strip()
    repo = repo.strip()

    # Remove .git suffix if present
    if repo.endswith(".git"):
        repo = repo[:-4]

    result = {"owner": owner, "repo": repo, "type": repo_type}

    if full_path:
        result["full_path"] = full_path

    if local_path:
        result["local_path"] = local_path

    return result
