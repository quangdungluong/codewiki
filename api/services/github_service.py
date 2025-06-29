import base64
from typing import Any, Dict, Optional

import requests

from utils.logger import logger


class GithubService:
    def __init__(self, owner: str, repo: str, token: Optional[str]):
        self.owner = owner
        self.repo = repo
        self.token = token

    def create_github_headers(self, token: Optional[str]) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        return headers

    def get_tree_data(self) -> Dict[str, Any]:
        tree_data = None
        api_error_details = None
        default_branch = None
        for branch in ["main", "master"]:
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees/{branch}?recursive=1"
            headers = self.create_github_headers(self.token)

            logger.info(f"Fetching repository structure from branch: {branch}")
            try:
                response = requests.get(api_url, headers=headers)

                if response.ok:
                    default_branch = branch
                    tree_data = response.json()
                    logger.info("Successfully fetched repository structure")
                    break
                else:
                    error_data = response.text
                    api_error_details = (
                        f"Status: {response.status_code}, Response: {error_data}"
                    )
                    logger.warning(
                        f"Failed to fetch branch {branch}: {api_error_details}"
                    )
            except Exception as e:
                logger.error(f"Network error fetching branch {branch}: {e}")

        if not tree_data or "tree" not in tree_data:
            if api_error_details:
                raise Exception(
                    f"Could not fetch repository structure. API Error: {api_error_details}"
                )
            else:
                raise Exception(
                    "Could not fetch repository structure. Repository might not exist, be empty or private."
                )

        # Convert tree data to a string representation
        file_tree_data = "\n".join(
            [item["path"] for item in tree_data["tree"] if item["type"] == "blob"]
        )
        return file_tree_data, default_branch

    def get_readme(self) -> str:
        try:
            headers = self.create_github_headers(self.token)

            readme_response = requests.get(
                f"https://api.github.com/repos/{self.owner}/{self.repo}/readme",
                headers=headers,
            )

            if readme_response.ok:
                readme_data = readme_response.json()
                readme_content = base64.b64decode(readme_data["content"]).decode(
                    "utf-8"
                )
                return readme_content
            else:
                logger.error(
                    f"Could not fetch README.md, status: {readme_response.status_code}"
                )
                return ""

        except Exception as e:
            logger.info(f"Could not fetch README.md, continuing with empty README: {e}")
            return ""
