import traceback
from typing import List

import google.generativeai as genai
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.rag import RAG
from utils.logger import logger
from utils.token_utils import count_tokens

router = APIRouter(prefix="/chat/completions/stream")


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatCompletionRequest(BaseModel):
    repo_url: str = Field(..., description="URL of the repository to query")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")


@router.post("/")
async def chat_completions_stream(request: ChatCompletionRequest):
    """Stream a chat completion response directly using Google Generative AI"""
    try:
        input_too_large = False
        if request.messages and len(request.messages) > 0:
            last_message = request.messages[-1]
            if hasattr(last_message, "content") and last_message.content:
                tokens = count_tokens(last_message.content)
                if tokens > 8000:
                    input_too_large = True
                    logger.warning(
                        f"Input too large: {tokens} tokens. Skipping request."
                    )
        try:
            request_rag = RAG(provider="google", model="gemini-2.5-pro")
            request_rag.prepare_retriever(request.repo_url, "github")
        except Exception as e:
            traceback.print_exc()
            error_msg = f"Error preparing RAG: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # validate request
        if not request.messages or len(request.messages) == 0:
            raise HTTPException(status_code=400, detail="No messages provided")

        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(
                status_code=400, detail="Last message must be from the user"
            )

        for i in range(0, len(request.messages) - 1, 2):
            if i + 1 < len(request.messages):
                user_msg = request.messages[i]
                assistant_msg = request.messages[i + 1]

                if user_msg.role == "user" and assistant_msg.role == "assistant":
                    request_rag.memory.add_dialog_turn(
                        user_msg.content, assistant_msg.content
                    )

        query = last_message.content
        context_text = ""
        retrieved_documents = None

        if not input_too_large:
            try:
                rag_query = query
                retrieved_documents = request_rag(rag_query)
                if retrieved_documents and retrieved_documents[0].documents:
                    documents = retrieved_documents[0].documents
                    logger.info(f"Retrieved {len(documents)} documents")
                    docs_by_file = {}
                    for doc in documents:
                        file_path = doc.meta_data.get("file_path", "unknown")
                        if file_path not in docs_by_file:
                            docs_by_file[file_path] = []
                        docs_by_file[file_path].append(doc)

                    context_parts = []
                    for file_path, docs in docs_by_file.items():
                        context_parts.append(f"## File Path: {file_path}\n\n")
                        content = "\n\n".join([doc.text for doc in docs])
                        context_parts.append(f"{content}\n\n")

                    context_text = "\n\n" + "-" * 10 + "\n\n".join(context_parts)
                else:
                    logger.warning("No documents retrieved from RAG")
            except Exception as e:
                traceback.print_exc()
                error_msg = f"Error in RAG query: {str(e)}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)

        # Get repository information
        repo_url = request.repo_url
        repo_name = repo_url.split("/")[-1] if "/" in repo_url else repo_url
        system_prompt = f"""<role>
You are an expert code analyst examining the repository: {repo_url} ({repo_name}).
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
</style>"""

        conversation_history = ""
        for turn_id, turn in request_rag.memory().items():
            if (
                not isinstance(turn_id, int)
                and hasattr(turn, "user_query")
                and hasattr(turn, "assistant_response")
            ):
                conversation_history += f"<turn>\n<user>{turn.user_query.query_str}</user>\n<assistant>{turn.assistant_response.response_str}</assistant>\n</turn>\n"

        prompt = f"/no_think {system_prompt}\n\n"
        if conversation_history:
            prompt += f"\n\n{conversation_history}"

        CONTEXT_START = "<START_OF_CONTEXT>"
        CONTEXT_END = "<END_OF_CONTEXT>"
        if context_text.strip():
            prompt += f"{CONTEXT_START}\n{context_text}\n{CONTEXT_END}\n\n"
        else:
            prompt += "<note>Answering without retrieval augmentation.</note>\n\n"

        prompt += f"<query>\n{query}\n</query>\n\nAssistant: "
        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
            },
        )

        async def response_stream():
            try:
                response = model.generate_content(prompt, stream=True)
                for chunk in response:
                    if hasattr(chunk, "text"):
                        yield chunk.text
            except Exception as e:
                logger.error(f"Error in streaming response: {str(e)}")

        return StreamingResponse(response_stream(), media_type="text/event-stream")

    except Exception as e_handler:
        traceback.print_exc()
        error_msg = f"Error in streaming chat completion: {str(e_handler)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
