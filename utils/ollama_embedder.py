import adalflow
from adalflow.core.component import DataComponent
from adalflow.core.types import Document
from tqdm import tqdm

from utils.logger import logger


class OllamaDocumentProcessor(DataComponent):
    """
    Process documents for Ollama embeddings by processing one document at a time.
    Adalflow Ollama Client does not support batch embedding, so we need to process each document individually.
    """

    def __init__(self, embedder: adalflow.Embedder) -> None:
        super().__init__()
        self.embedder = embedder

    def __call__(self, documents: list[Document]) -> list[Document]:
        output = []
        logger.info(
            f"Processing {len(documents)} documents individually for Ollama embeddings"
        )

        for i, doc in enumerate(tqdm(documents)):
            try:
                # Get embedding for a single document
                result = self.embedder(input=doc.text)
                if result.data and len(result.data) > 0:
                    embedding = result.data[0].embedding
                    doc.vector = embedding
                    output.append(doc)
                else:
                    logger.warning(
                        f"Failed to get embedding for document {i}, skipping"
                    )
            except Exception as e:
                logger.error(f"Error processing document {i}: {e}, skipping")

        logger.info(
            f"Successfully processed {len(output)}/{len(documents)} documents with embeddings"
        )
        return output
