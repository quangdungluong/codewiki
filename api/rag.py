import adalflow
import adalflow.core
import traceback
from utils.logger import logger
from dataclasses import dataclass, field
from uuid import uuid4
from adalflow import GoogleGenAIClient, OllamaClient
from utils.localdb_manager import LocalDBManager
from adalflow.components.retriever.faiss_retriever import (
    FAISSRetriever,
    RetrieverOutput,
)
from typing import Union, List


@dataclass
class UserQuery:
    query_str: str


@dataclass
class AssistantResponse:
    response_str: str


@dataclass
class DialogTurn:
    id: str
    user_query: UserQuery
    assistant_response: AssistantResponse


@dataclass
class RAGAnswer(adalflow.DataClass):
    rationale: str = field(
        default="", metadata={"desc": "Chain of thoughts for the answer."}
    )
    answer: str = field(
        default="",
        metadata={
            "desc": "Answer to the user query, formatted in markdown for beautiful rendering with react-markdown. DO NOT include ``` triple backticks fences at the beginning or end of your answer."
        },
    )

    __output_fields__ = ["rationale", "answer"]


system_prompt = r"""
You are a code assistant which answers user questions on a Github Repo.
You will receive user query, relevant context, and past conversation history.

LANGUAGE DETECTION AND RESPONSE:
- Detect the language of the user's query
- Respond in the SAME language as the user's query
- IMPORTANT:If a specific language is requested in the prompt, prioritize that language over the query language

FORMAT YOUR RESPONSE USING MARKDOWN:
- Use proper markdown syntax for all formatting
- For code blocks, use triple backticks with language specification (```python, ```javascript, etc.)
- Use ## headings for major sections
- Use bullet points or numbered lists where appropriate
- Format tables using markdown table syntax when presenting structured data
- Use **bold** and *italic* for emphasis
- When referencing file paths, use `inline code` formatting

IMPORTANT FORMATTING RULES:
1. DO NOT include ```markdown fences at the beginning or end of your answer
2. Start your response directly with the content
3. The content will already be rendered as markdown, so just provide the raw markdown content

Think step by step and ensure your answer is well-structured and visually organized.
"""

# Template for RAG
RAG_TEMPLATE = r"""<START_OF_SYS_PROMPT>
{{system_prompt}}
{{output_format_str}}
<END_OF_SYS_PROMPT>
{# OrderedDict of DialogTurn #}
{% if conversation_history %}
<START_OF_CONVERSATION_HISTORY>
{% for key, dialog_turn in conversation_history.items() %}
{{key}}.
User: {{dialog_turn.user_query.query_str}}
You: {{dialog_turn.assistant_response.response_str}}
{% endfor %}
<END_OF_CONVERSATION_HISTORY>
{% endif %}
{% if contexts %}
<START_OF_CONTEXT>
{% for context in contexts %}
{{loop.index }}.
File Path: {{context.meta_data.get('file_path', 'unknown')}}
Content: {{context.text}}
{% endfor %}
<END_OF_CONTEXT>
{% endif %}
<START_OF_USER_PROMPT>
{{input_str}}
<END_OF_USER_PROMPT>
"""


class CustomConversation:
    """Custom implementation of Conversation to fix the list assignment index out of range error"""

    def __init__(self):
        self.dialog_turns = []

    def append_dialog_turn(self, dialog_turn):
        """Safely append a dialog turn to the conversation"""
        if not hasattr(self, "dialog_turns"):
            self.dialog_turns = []
        self.dialog_turns.append(dialog_turn)


class Memory(adalflow.core.component.DataComponent):
    def __init__(self):
        super().__init__()
        self.current_conversation = CustomConversation()

    def call(self):
        all_diaglog_turns = {}
        try:
            if hasattr(self.current_conversation, "dialog_turns"):
                if self.current_conversation.dialog_turns:
                    for i, turn in enumerate(self.current_conversation.dialog_turns):
                        if hasattr(turn, "id") and turn.id is not None:
                            all_diaglog_turns[turn.id] = turn
                        else:
                            logger.warning(
                                f"Skipping invalid dialog turn at index {i}: {turn}"
                            )
            else:
                logger.info("No dialog turns found in the current conversation.")
                self.current_conversation.dialog_turns = []
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error in Memory component: {e}")
        return all_diaglog_turns

    def add_dialog_turn(self, user_query: str, assistant_response: str):
        try:
            dialog_turn = DialogTurn(
                id=str(uuid4()),
                user_query=UserQuery(query_str=user_query),
                assistant_response=AssistantResponse(response_str=assistant_response),
            )

            if not hasattr(self.current_conversation, "append_dialog_turn"):
                self.current_conversation = CustomConversation()

            if not hasattr(self.current_conversation, "dialog_turns"):
                self.current_conversation.dialog_turns = []

            self.current_conversation.dialog_turns.append(dialog_turn)
            return True

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error adding dialog turn: {e}")
            return


class RAG(adalflow.Component):
    def __init__(self, provider: str = "google", model: str = None):
        super().__init__()

        self.provider = provider
        self.model = model

        self.memory = Memory()
        self.embedder = adalflow.Embedder(
            model_client=OllamaClient(), model_kwargs={"model": "nomic-embed-text"}
        )

        def ollama_embedder(query: Union[str, list]):
            if isinstance(query, list):
                query = query[0]
            return self.embedder(input=query)

        self.query_embedder = ollama_embedder

        self.initialize_db_manager()

        data_parser = adalflow.DataClassParser(
            data_class=RAGAnswer, return_data_class=True
        )

        format_instruction = (
            data_parser.get_output_format_str()
            + """
IMPORTANT FORMATTING RULES:
1. DO NOT include your thinking or reasoning process in the output
2. Provide only the final, polished answer
3. DO NOT include ```markdown fences at the beginning or end of your answer
4. DO NOT wrap your response in any kind of fences
5. Start your response directly with the content
6. The content will already be rendered as markdown
7. Do not use backslashes before special characters like [ ] { } in your answer
8. When listing tags or similar items, write them as plain text without escape characters
9. For pipe characters (|) in text, write them directly without escaping them
"""
        )

        self.generator = adalflow.Generator(
            template=RAG_TEMPLATE,
            prompt_kwargs={
                "output_format_str": format_instruction,
                "conversation_history": self.memory(),
                "system_prompt": system_prompt,
                "contexts": None,
            },
            model_client=GoogleGenAIClient(),
            model_kwargs={
                "model": "gemini-2.0-flash",
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
            },
            output_processors=data_parser,
        )

    def initialize_db_manager(self):
        self.db_manager = LocalDBManager()
        self.transformed_docs = []

    def prepare_retriever(
        self, repo_url: str, type: str = "github", access_token: str = None
    ):
        self.initialize_db_manager()
        self.repo_url = repo_url
        self.transformed_docs = self.db_manager.prepare_db(
            repo_url=repo_url, access_token=access_token
        )
        logger.info(f"Prepared {len(self.transformed_docs)} documents for retrieval.")

        try:
            self.retriever = FAISSRetriever(
                embedder=self.query_embedder,
                top_k=20,
                documents=self.transformed_docs,
                document_map_func=lambda doc: doc.vector,
            )
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error creating retriever: {e}")
            raise e

    def call(self, query: str):
        try:
            logger.info(f"Processing query: {query[:50]}\n...\n{query[-50:]}")
            retrieved_documents: List[RetrieverOutput] = self.retriever(query)
            retrieved_documents[0].documents = [
                self.transformed_docs[doc_id]
                for doc_id in retrieved_documents[0].doc_indices
            ]
            return retrieved_documents

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error in RAG call: {e}")
            error_response = RAGAnswer(
                rationale="Error occurred while processing the query.",
                answer=f"Error retrieving documents: {str(e)}",
            )
            return error_response, []
