import os
import traceback
from typing import List, Optional

from adalflow.core.db import LocalDB
from adalflow.utils import get_adalflow_default_root_path

from utils.document_pipeline import DocumentTransformer, RecursiveDocumentReader
from utils.logger import logger
from utils.repo_downloader import RepoDownloader


class LocalDBManager:
    def __init__(self):
        self.db = None
        self.repo_url = None
        self.repo_paths = None

    def reset_db(self):
        """Reset the database to its initial state."""
        self.db = None
        self.repo_url = None
        self.repo_paths = None

    def prepare_db(
        self,
        repo_url: str,
        access_token: str = None,
        excluded_dirs: List[str] = None,
        excluded_files: List[str] = None,
        included_dirs: List[str] = None,
        included_files: List[str] = None,
    ):
        self.reset_db()
        self._create_repo(repo_url, access_token)
        return self.prepare_db_index(
            excluded_dirs=excluded_dirs,
            excluded_files=excluded_files,
            included_dirs=included_dirs,
            included_files=included_files,
        )

    def _create_repo(self, repo_url: str, access_token: Optional[str] = None):
        """Create a repository with the given URL and access token."""
        logger.info(f"Preparing repo storage for {repo_url}")
        try:
            root_path = "./.cache"
            if repo_url.startswith("https://") or repo_url.startswith("http://"):
                repo_name = repo_url.split("/")[-1].replace(".git", "")
                save_repo_path = os.path.join(root_path, "repos", repo_name)
                # Download repository if it does not exist
                RepoDownloader(
                    repo_url=repo_url,
                    local_path=save_repo_path,
                    access_token=access_token,
                ).download()

                save_db_file = os.path.join(root_path, "db", f"{repo_name}.pkl")
                os.makedirs(os.path.dirname(save_db_file), exist_ok=True)

                self.repo_paths = {
                    "repo_url": repo_url,
                    "save_repo_path": save_repo_path,
                    "save_db_file": save_db_file,
                }
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Failed to create repo storage for {repo_url}: {e}")

    def prepare_db_index(
        self,
        excluded_dirs: List[str] = None,
        excluded_files: List[str] = None,
        included_dirs: List[str] = None,
        included_files: List[str] = None,
    ):
        if self.repo_paths and os.path.exists(self.repo_paths.get("save_db_file")):
            try:
                self.db = LocalDB.load_state(filepath=self.repo_paths["save_db_file"])
                documents = self.db.get_transformed_data(key="split_and_embed")
                if documents:
                    logger.info(f"Loaded {len(documents)} documents from the database.")
                    return documents
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error loading database: {e}")

        logger.info("Creating new database index...")
        document_reader = RecursiveDocumentReader(
            path=self.repo_paths["save_repo_path"],
            excluded_dirs=excluded_dirs,
            excluded_files=excluded_files,
            included_dirs=included_dirs,
            included_files=included_files,
        )
        documents = document_reader.read_documents()
        self.db = DocumentTransformer(
            documents=documents, db_path=self.repo_paths["save_db_file"]
        ).transform_and_save()
        logger.info(f"Total documents processed: {len(documents)}")
        transformed_documents = self.db.get_transformed_data(key="split_and_embed")
        logger.info(
            f"Total transformed documents with embeddings: {len(transformed_documents)}"
        )
        return transformed_documents

    def prepare_retriever(self, repo_url: str, access_token: Optional[str] = None):
        return self.prepare_db(repo_url=repo_url, access_token=access_token)
