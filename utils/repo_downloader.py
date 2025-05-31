import os
import subprocess
import traceback
from urllib.parse import ParseResult, urlparse, urlunparse

from utils.logger import logger


class RepoDownloader:
    def __init__(self, repo_url: str, local_path: str, access_token: str = None):
        self.repo_url = repo_url
        self.local_path = local_path
        self.access_token = access_token

    def download(self):
        try:
            # Check if repository already exists
            if os.path.exists(self.local_path) and os.listdir(self.local_path):
                logger.info(
                    f"Repository already exists at {self.local_path}. Skipping clone."
                )
                return

            logger.info(f"Preparing to clone repository to {self.local_path}")
            subprocess.run(
                ["git", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            os.makedirs(self.local_path, exist_ok=True)

            clone_url = self.repo_url
            if self.access_token:
                logger.info(f"Cloning repository with access token")
                parsed_url: ParseResult = urlparse(self.repo_url)
                clone_url = urlunparse(
                    parsed_url.scheme,
                    f"{self.access_token}@{parsed_url.netloc}",
                    parsed_url.path,
                    "",
                    "",
                    "",
                )

            logger.info(f"Cloning repository from {self.repo_url} to {self.local_path}")
            result = subprocess.run(
                ["git", "clone", clone_url, self.local_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info(f"Repository cloned successfully")
            return
        except Exception as e:
            traceback.print_exc()
            raise ValueError(f"Error downloading repository: {str(e)}")
