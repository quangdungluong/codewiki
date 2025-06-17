import glob
import os
import traceback
from typing import List, Optional

import adalflow
from adalflow import GoogleGenAIClient, OllamaClient
from adalflow.components.data_process import TextSplitter, ToEmbeddings
from adalflow.core.db import LocalDB
from adalflow.core.types import Document

from config import DEFAULT_EXCLUDED_DIRS, DEFAULT_EXCLUDED_FILES
from utils.constants import MAX_EMBEDDING_TOKEN
from utils.logger import logger
from utils.ollama_embedder import OllamaDocumentProcessor
from utils.token_utils import count_tokens


class RecursiveDocumentReader:
    def __init__(
        self,
        path: str,
        excluded_dirs: List[str] = None,
        excluded_files: List[str] = None,
        included_dirs: List[str] = None,
        included_files: List[str] = None,
    ):
        self.path = path
        self.excluded_dirs = list(set(excluded_dirs if excluded_dirs else []))
        self.excluded_files = list(set(excluded_files if excluded_files else []))
        self.included_dirs = list(set(included_dirs if included_dirs else []))
        self.included_files = list(set(included_files if included_files else []))
        self.code_extensions = [
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".go",
            ".rs",
            ".jsx",
            ".tsx",
            ".html",
            ".css",
            ".php",
            ".swift",
            ".cs",
        ]
        self.doc_extensions = [".md", ".txt", ".rst", ".json", ".yaml", ".yml"]

    def _should_process_file(self, file_path: str, use_inclusion_mode: bool) -> bool:
        file_path_parts = os.path.normpath(file_path).split(os.sep)
        file_name = os.path.basename(file_path)
        if use_inclusion_mode:
            is_included = False
            # Check if the file is in the included directories
            for inc_dir in self.included_dirs:
                if inc_dir in file_path_parts:
                    is_included = True
                    break
            # Check if the file matches the included files
            for inc_file in self.included_files:
                if inc_file == file_name or file_name.endswith(inc_file):
                    is_included = True
                    break

            if not self.included_dirs and not self.included_files:
                is_included = True

            return is_included
        else:
            is_excluded = False
            # Check if the file is in the excluded directories
            for exc_dir in self.excluded_dirs:
                if exc_dir in file_path_parts:
                    is_excluded = True
                    break
            # Check if the file matches the excluded files
            for exc_file in self.excluded_files:
                if exc_file == file_name or file_name.endswith(exc_file):
                    is_excluded = True
                    break
            return not is_excluded

    def read_documents(self):
        documents = []
        use_inclusion_mode = (self.included_dirs and len(self.included_dirs) > 0) or (
            self.included_files and len(self.included_files) > 0
        )
        if use_inclusion_mode:
            self.excluded_dirs = []
            self.excluded_files = []
            logger.info("Using inclusion mode")
        else:
            self.excluded_dirs = list(
                set(self.excluded_dirs) | set(DEFAULT_EXCLUDED_DIRS)
            )
            self.excluded_files = list(
                set(self.excluded_files) | set(DEFAULT_EXCLUDED_FILES)
            )
            self.included_dirs = []
            self.included_files = []
            logger.info("Using exclusion mode")

        logger.info(f"Reading documents from {self.path}")

        # Process code files first
        for ext in self.code_extensions:
            files = glob.glob(f"{self.path}/**/*{ext}", recursive=True)
            for file_path in files:
                if not self._should_process_file(file_path, use_inclusion_mode):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        relative_path = os.path.relpath(file_path, self.path)
                        # Determine if the file is a code file
                        is_implementation = (
                            not relative_path.startswith("test_")
                            and not relative_path.startswith("app_")
                            and "test" not in relative_path.lower()
                        )
                        # Check the token count
                        token_count = count_tokens(content)
                        if token_count > MAX_EMBEDDING_TOKEN * 10:
                            logger.warning(
                                f"Skipping {relative_path} due to high token count: {token_count}"
                            )
                            continue

                        doc = Document(
                            text=content,
                            meta_data={
                                "file_path": relative_path,
                                "is_implementation": is_implementation,
                                "type": ext[1:],
                                "is_code": True,
                                "title": relative_path,
                                "token_count": token_count,
                            },
                        )
                        documents.append(doc)

                except Exception as e:
                    traceback.print_exc()
                    logger.error(f"Error reading file {file_path}: {e}")
                    continue

        # Process document files
        for ext in self.doc_extensions:
            files = glob.glob(f"{self.path}/**/*{ext}", recursive=True)
            for file_path in files:
                if not self._should_process_file(file_path, use_inclusion_mode):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        relative_path = os.path.relpath(file_path, self.path)
                        # Check the token count
                        token_count = count_tokens(content)
                        if token_count > MAX_EMBEDDING_TOKEN:
                            logger.warning(
                                f"Skipping {relative_path} due to high token count: {token_count}"
                            )
                            continue

                        doc = Document(
                            text=content,
                            meta_data={
                                "file_path": relative_path,
                                "type": ext[1:],
                                "is_code": False,
                                "is_implementation": False,
                                "title": relative_path,
                                "token_count": token_count,
                            },
                        )
                        documents.append(doc)

                except Exception as e:
                    traceback.print_exc()
                    logger.error(f"Error reading file {file_path}: {e}")
                    continue
        logger.info(f"Found {len(documents)} documents in {self.path}")
        return documents


class DocumentTransformer:
    def __init__(self, documents: List[Document], db_path: str):
        self.documents = documents
        self.db_path = db_path
        self.data_transformer = self._prepare_data_pipeline()

    def _prepare_data_pipeline(self):
        splitter = TextSplitter(split_by="word", chunk_size=500, chunk_overlap=100)
        embedder = adalflow.Embedder(
            model_client=OllamaClient(), model_kwargs={"model": "nomic-embed-text"}
        )
        embedder_transformer = OllamaDocumentProcessor(embedder=embedder)
        data_transformer = adalflow.Sequential(splitter, embedder_transformer)
        return data_transformer

    def transform_and_save(self):
        db = LocalDB()
        db.register_transformer(
            transformer=self.data_transformer, key="split_and_embed"
        )
        db.load(self.documents)
        db.transform(key="split_and_embed")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        db.save_state(filepath=self.db_path)
        return db
