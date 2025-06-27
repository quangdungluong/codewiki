import os
import traceback
from typing import Any, Dict, List

import google.generativeai as genai
from fastapi import WebSocket, WebSocketDisconnect

from api.models import ChatCompletionRequest, ChatMessage
from api.rag import RAG
from utils.logger import logger
from utils.token_utils import count_tokens

google_api_key = os.environ.get("GOOGLE_API_KEY")


async def handle_websocket_chat(websocket: WebSocket):
    await websocket.accept()

    try:
        request_data = await websocket.receive_json()
        request = ChatCompletionRequest(**request_data)
        # logger.info(f"Received WebSocket request: {request}")

        # Create new RAG instance
        try:
            request_rag = RAG(provider=request.provider, model=request.model)
            request_rag.prepare_retriever(request.repo_url, type=request.type)
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error initializing RAG instance: {e}")
            await websocket.send_text(f"Error initializing RAG instance: {str(e)}")
            await websocket.close()
            return

        # Check if the request is very large
        input_too_large = False
        if request.messages and len(request.messages) > 0:
            last_message = request.messages[-1]
            if hasattr(last_message, "content") and last_message.content:
                tokens = count_tokens(last_message.content)
                logger.info(f"Token count for last message: {tokens}")
                if tokens > 8000:
                    logger.warning("Request exceeds token limit")
                    input_too_large = True

        # validate the request
        if not request.messages or len(request.messages) == 0:
            await websocket.send_text("Error: No messages provided in the request.")
            await websocket.close()
            return

        last_message = request.messages[-1]
        if last_message.role != "user":
            await websocket.send_text("Error: Last message must be from the user.")
            await websocket.close()
            return

        # Process previous messages to build conversation history
        for i in range(0, len(request.messages) - 1, 2):
            if i + i < len(request.messages):
                user_message = request.messages[i]
                assistant_message = request.messages[i + 1]
                if (
                    user_message.role == "user"
                    and assistant_message.role == "assistant"
                ):
                    # TODO: add dialogue history processing logic here
                    pass

        query = last_message.content

        # Only proceed if the input is not too large
        context_text = ""
        retrieved_documents = []
        if not input_too_large:
            try:
                retrieved_documents = request_rag(query)
                if retrieved_documents and retrieved_documents[0].documents:
                    # Format the context for the prompt in a more structured way
                    documents = retrieved_documents[0].documents
                    logger.info(f"Retrieved {len(documents)} documents for the query.")
                    # Group the documents by file
                    docs_by_file: Dict[str, List] = {}
                    for doc in documents:
                        file_path = doc.meta_data.get("file_path", "unknown")
                        if file_path not in docs_by_file:
                            docs_by_file[file_path] = []
                        docs_by_file[file_path].append(doc)
                    # Format the context text with file path grouping
                    context_parts = []
                    for file_path, docs in docs_by_file.items():
                        header = f"## File Path: {file_path}\n\n"
                        content = "\n\n".join([doc.text for doc in docs])
                        context_parts.append(f"{header}{content}")
                    context_text = "\n\n" + "-" * 10 + "\n\n".join(context_parts)
                else:
                    logger.warning("No documents retrieved for the query.")

            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error retrieving documents: {e}")
                context_text = ""

        # Get repository information
        repo_url = request.repo_url
        repo_name = repo_url.split("/")[-1] if "/" in repo_url else repo_url
        repo_type = request.type

        system_prompt = f""""
<role>
You are an expert code analyst examining the {repo_type} repository: {repo_url} ({repo_name}).
You provide direct, concise, and accurate information about code repositories.
You NEVER start responses with markdown headers or code fences.
IMPORTANT:You MUST respond in English language.
</role>

<guidelines>
- Answer the user's question directly without ANY preamble or filler phrases
- DO NOT include any rationale, explanation, or extra comments.
- DO NOT start with preambles like "Okay, here's a breakdown" or "Here's an explanation"
- DO NOT start with markdown headers like "## Analysis of..." or any file path references
- DO NOT start with ```markdown code fences
- DO NOT end your response with ``` closing fences
- DO NOT start by repeating or acknowledging the question
- JUST START with the direct answer to the question

<example_of_what_not_to_do>
```markdown
## Analysis of `adalflow/adalflow/datasets/gsm8k.py`

This file contains...
```
</example_of_what_not_to_do>

- Format your response with proper markdown including headings, lists, and code blocks WITHIN your answer
- For code analysis, organize your response with clear sections
- Think step by step and structure your answer logically
- Start with the most relevant information that directly addresses the user's query
- Be precise and technical when discussing code
- Your response language should be in the same language as the user's query
</guidelines>

<style>
- Use concise, direct language
- Prioritize accuracy over verbosity
- When showing code, include line numbers and file paths when relevant
- Use markdown formatting to improve readability
</style>
        """

        conversation_history = ""
        for turn_id, turn in request_rag.memory().items():
            if (
                not isinstance(turn_id, int)
                and hasattr(turn, "user_query")
                and hasattr(turn, "assistant_response")
            ):
                user_query = turn.user_query.query_str
                assistant_response = turn.assistant_response.response_str
                conversation_history += f"<turn>\n<user>{user_query}</user>\n<assistant>{assistant_response}</assistant>\n</turn>\n"

        prompt = f"/no_think {system_prompt}\n\n"
        if conversation_history:
            prompt += f"<conversation_history>\n{conversation_history}</conversation_history>\n\n"

        # Only add context if it exists
        CONTEXT_START = "<START_OF_CONTEXT>"
        CONTEXT_END = "<END_OF_CONTEXT>"
        if context_text:
            prompt += f"{CONTEXT_START}\n{context_text}\n{CONTEXT_END}\n\n"
        else:
            logger.info("No context text available, proceeding without it.")
            prompt += f"<note>Answering without retrieval augmentation.</note>\n\n"

        prompt += f"<query>\n{query}\n</query>\n\n"

        model = genai.GenerativeModel(
            model_name=request.model,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
            },
        )

        response = model.generate_content(prompt, stream=True)
        # Stream the response
        for chunk in response:
            if hasattr(chunk, "text"):
                await websocket.send_text(chunk.text)
        await websocket.close()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error in WebSocket communication: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
            await websocket.close()
        except:
            pass
