import os
import sys

import uvicorn
from dotenv import load_dotenv

from utils.logger import logger

load_dotenv()

if __name__ == "__main__":
    from api.api import app

    uvicorn.run(
        "api.api:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8001)),
        reload=True,
    )
