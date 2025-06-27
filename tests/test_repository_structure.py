import os
import sys

sys.path.insert(0, os.getcwd())
import asyncio

from dotenv import load_dotenv

from utils.repository_structure import RepositoryStructureFetcher

load_dotenv()


async def main():
    fetcher = RepositoryStructureFetcher(
        repo_info={
            "type": "web",
        },
        repo_url="https://github.com/AsyncFuncAI/deepwiki-open",
        owner="AsyncFuncAI",
        repo="deepwiki-open",
        token=os.getenv("GITHUB_API_KEY", ""),
    )
    await fetcher.fetch_repository_structure()


if __name__ == "__main__":
    asyncio.run(main())
