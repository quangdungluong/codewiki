import os
import json
import httpx
import gradio as gr
from utils.repository_structure import RepositoryStructureFetcher
from utils.logger import logger
from dotenv import load_dotenv

load_dotenv()
# Configuration
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://localhost:8001")
# WS_BASE_URL = SERVER_BASE_URL.replace("http", "ws") # Not used directly by UI client


async def call_generate_full_wiki_api(payload: dict):
    logger.info(payload)

    fetcher = RepositoryStructureFetcher(
        repo_info={
            "type": "web",
        },
        repo_url="https://github.com/quangdungluong/DeepStream-YOLOv11",
        owner="quangdungluong",
        repo="DeepStream-YOLOv11",
        token=os.getenv("GITHUB_API_KEY", ""),
    )
    await fetcher.fetch_repository_structure()
    return {}


# Gradio UI for the frontend
def create_ui():
    """Create a Gradio UI for the wiki generator."""
    with gr.Blocks(
        title="CodeWiki Generator",
        css=".gradio-container {max-width: 960px !important; margin: auto !important;}",
    ) as app:
        gr.Markdown("# CodeWiki Generator")

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Repository Details")
                repo_type = gr.Dropdown(
                    label="Repository Type",
                    choices=["github", "gitlab", "bitbucket", "local"],
                    value="github",
                )
                owner_input = gr.Textbox(
                    label="Owner (e.g., langchain-ai)", visible=True
                )
                repo_input = gr.Textbox(
                    label="Repository Name (e.g., local-deep-researcher)", visible=True
                )
                local_path_input = gr.Textbox(
                    label="Local Path to Repository", visible=False
                )
                repo_url_override = gr.Textbox(
                    label="Full Repository URL (Optional, overrides above if provided for non-local types)",
                    placeholder="e.g., https://custom.example.com/owner/repo.git",
                )
                token_input = gr.Textbox(
                    label="Access Token (optional, e.g., GitHub PAT)", type="password"
                )

                gr.Markdown("### Generation Parameters")
                language_input = gr.Dropdown(
                    label="Language",
                    choices=[
                        "en",
                        "ja",
                        "zh",
                        "es",
                        "fr",
                        "de",
                        "ko",
                        "pt",
                        "ru",
                        "it",
                        "vi",
                    ],
                    value="en",
                )
                provider_input = gr.Dropdown(
                    label="AI Provider",
                    choices=[
                        "google",
                        "openai",
                        "openrouter",
                        "ollama",
                        "anthropic",
                        "azure_openai",
                        "bedrock",
                    ],
                    value="google",
                )
                model_input = gr.Textbox(
                    label="Model Name", value="gemini-1.5-flash-latest"
                )  # Updated default

                is_custom_model_checkbox = gr.Checkbox(
                    label="Use Custom Model Endpoint/Parameters", value=False
                )
                custom_model_input = gr.Textbox(
                    label="Custom Model Name/Path (if applicable)",
                    visible=False,
                    placeholder="e.g., for Ollama: llama3; for vLLM: user/my-model-vllm",
                )

                excluded_dirs_input = gr.Textbox(
                    label="Excluded Directories (comma-separated)",
                    placeholder=".git,node_modules,__pycache__",
                )
                excluded_files_input = gr.Textbox(
                    label="Excluded Files (comma-separated, supports glob patterns)",
                    placeholder="*.log,*.tmp,package-lock.json",
                )

                wiki_mode_input = gr.Dropdown(
                    label="Wiki Mode",
                    choices=["comprehensive", "concise"],
                    value="comprehensive",
                )
                use_cache_checkbox = gr.Checkbox(
                    label="Use Cache (if available for this repo & settings)",
                    value=True,
                )

                generate_button = gr.Button("Generate Wiki", variant="primary")

            with gr.Column(scale=3):
                gr.Markdown("### Output")
                status_output = gr.Textbox(label="Status", lines=2, interactive=False)
                json_output = gr.JSON(label="Generated Wiki Structure", scale=2)

        # Conditional visibility logic
        def update_repo_inputs(repo_type_val):
            if repo_type_val == "local":
                return {
                    owner_input: gr.update(visible=False),
                    repo_input: gr.update(visible=False),
                    local_path_input: gr.update(visible=True),
                }
            else:
                return {
                    owner_input: gr.update(visible=True),
                    repo_input: gr.update(visible=True),
                    local_path_input: gr.update(visible=False),
                }

        repo_type.change(
            fn=update_repo_inputs,
            inputs=repo_type,
            outputs=[owner_input, repo_input, local_path_input],
        )

        def update_custom_model_input(is_custom_model_val):
            return gr.update(visible=is_custom_model_val)

        is_custom_model_checkbox.change(
            fn=update_custom_model_input,
            inputs=is_custom_model_checkbox,
            outputs=custom_model_input,
        )

        async def on_generate_click_handler(
            repo_type_val,
            owner_val,
            repo_val,
            local_path_val,
            repo_url_override_val,
            token_val,
            language_val,
            provider_val,
            model_val,
            is_custom_model_val,
            custom_model_val,
            excluded_dirs_val,
            excluded_files_val,
            wiki_mode_val,
            use_cache_val,
        ):
            # status_output.update("Processing request... Preparing to generate wiki.")

            repo_details = {
                "type": repo_type_val,
                "owner": owner_val if repo_type_val != "local" else None,
                "repo": repo_val if repo_type_val != "local" else None,
                "local_path": local_path_val if repo_type_val == "local" else None,
                "repo_url_override": (
                    repo_url_override_val if repo_url_override_val else None
                ),
            }

            generation_params = {
                "token": token_val if token_val else None,
                "language": language_val,
                "provider": provider_val,
                "model": model_val,
                "is_custom_model": is_custom_model_val,
                "custom_model_name": (
                    custom_model_val
                    if is_custom_model_val and custom_model_val
                    else None
                ),
                "excluded_dirs": excluded_dirs_val if excluded_dirs_val else None,
                "excluded_files": excluded_files_val if excluded_files_val else None,
                "wiki_mode": wiki_mode_val,
                "use_cache": use_cache_val,
            }

            payload = {
                "repo_details": repo_details,
                "generation_params": generation_params,
            }

            # status_output.update(
            #     f"Sending request to API: {json.dumps(payload, indent=2)}\nThis may take several minutes, especially for large repositories or first-time generation."
            # )

            try:
                result = await call_generate_full_wiki_api(payload)
                # status_output.update("Wiki generation complete!")
                return result
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                try:
                    error_json = e.response.json()
                    if isinstance(error_json, dict) and "detail" in error_json:
                        error_detail = error_json["detail"]
                    elif isinstance(error_json, str):
                        error_detail = error_json  # if backend returns plain string error in json response
                except:
                    pass  # Keep original text if not json or no 'detail' field
                # status_output.update(
                #     f"API Error: {e.response.status_code} - {error_detail}"
                # )
                return {
                    "error": f"API Error: {e.response.status_code} - {error_detail}",
                    "details": e.response.text,
                }
            except httpx.RequestError as e:
                # status_output.update(
                #     f"Request Error: Failed to connect to the API. Ensure the backend server is running at {SERVER_BASE_URL}. Details: {str(e)}"
                # )
                return {"error": f"Request Error: {str(e)}"}
            except Exception as e:
                # status_output.update(f"An unexpected error occurred: {str(e)}")
                return {"error": str(e)}

        generate_button.click(
            fn=on_generate_click_handler,
            inputs=[
                repo_type,
                owner_input,
                repo_input,
                local_path_input,
                repo_url_override,
                token_input,
                language_input,
                provider_input,
                model_input,
                is_custom_model_checkbox,
                custom_model_input,
                excluded_dirs_input,
                excluded_files_input,
                wiki_mode_input,
                use_cache_checkbox,
            ],
            outputs=[json_output],
        )

    return app


# Entry point
if __name__ == "__main__":
    app = create_ui()
    app.launch(
        server_name="0.0.0.0", server_port=7860, share=False
    )  # Set share=True to get a public link if needed
