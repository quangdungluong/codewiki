import asyncio
import base64
import json
import re
import traceback
import urllib.parse
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx
import requests
import websockets

from api.models import WikiCacheData, WikiStructureModel
from utils.constants import TARGET_SERVER_BASE_URL
from utils.logger import logger
from utils.models import WikiPage, WikiSection, WikiStructure


class RepositoryStructureFetcher:
    def __init__(
        self,
        repo_info: Dict[str, Any],
        repo_url: str,
        owner: str,
        repo: str,
        token: Optional[str] = None,
    ):
        self.repo_info = repo_info
        self.repo_url = repo_url
        self.owner = owner
        self.repo = repo
        self.token = token
        self.request_in_progress = False
        self.wiki_structure = None
        self.current_page_id = None
        self.generated_pages = {}
        self.pages_in_progress = set()
        self.error = None
        self.is_loading = False

    def create_github_headers(self, token: Optional[str]) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        return headers

    def extract_url_path(self, url: str) -> Optional[str]:
        if not url:
            return None
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path
            if path.startswith("/"):
                path = path[1:]
            return path
        except:
            return None

    def extract_url_domain(self, url: str) -> str:
        try:
            parsed_url = urlparse(url)
            return f"{parsed_url.scheme}://{parsed_url.netloc}"
        except:
            return "https://gitlab.com"

    async def fetch_repository_structure(
        self,
        update_task_status: Callable,
        task_id: str,
    ):
        # Reset previous state
        self.wiki_structure = None
        self.current_page_id = None
        self.generated_pages = {}
        self.pages_in_progress = set()
        self.error = None

        try:
            # Update loading state
            self.is_loading = True
            self.loading_message = "Fetching repository structure..."
            update_task_status(
                task_id, "processing", "Fetching repository structure..."
            )

            file_tree_data = ""
            readme_content = ""

            if self.repo_info["type"] == "local" and self.repo_info.get("local_path"):
                try:
                    response = requests.get(
                        f"{TARGET_SERVER_BASE_URL}/local_repo/structure?path={urllib.parse.quote(self.repo_info['local_path'])}"
                    )

                    if not response.ok:
                        error_data = response.text
                        raise Exception(
                            f"Local repository API error ({response.status_code}): {error_data}"
                        )

                    data = response.json()
                    file_tree_data = data["file_tree"]
                    readme_content = data["readme"]
                except Exception as err:
                    raise err

            elif self.repo_info["type"] == "web":
                # GitHub API approach
                # Try to get the tree data for common branch names
                tree_data = None
                api_error_details = ""

                for branch in ["main", "master"]:
                    api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees/{branch}?recursive=1"
                    headers = self.create_github_headers(self.token)

                    logger.info(f"Fetching repository structure from branch: {branch}")
                    try:
                        response = requests.get(api_url, headers=headers)

                        if response.ok:
                            tree_data = response.json()
                            logger.info("Successfully fetched repository structure")
                            break
                        else:
                            error_data = response.text
                            api_error_details = f"Status: {response.status_code}, Response: {error_data}"
                            logger.warning(
                                f"Failed to fetch branch {branch}: {api_error_details}"
                            )
                    except Exception as e:
                        traceback.print_exc()
                        logger.error(f"Network error fetching branch {branch}: {e}")

                if not tree_data or "tree" not in tree_data:
                    if api_error_details:
                        raise Exception(
                            f"Could not fetch repository structure. API Error: {api_error_details}"
                        )
                    else:
                        raise Exception(
                            "Could not fetch repository structure. Repository might not exist, be empty or private."
                        )

                # Convert tree data to a string representation
                file_tree_data = "\n".join(
                    [
                        item["path"]
                        for item in tree_data["tree"]
                        if item["type"] == "blob"
                    ]
                )

                # Try to fetch README.md content
                try:
                    headers = self.create_github_headers(self.token)

                    readme_response = requests.get(
                        f"https://api.github.com/repos/{self.owner}/{self.repo}/readme",
                        headers=headers,
                    )

                    if readme_response.ok:
                        readme_data = readme_response.json()
                        readme_content = base64.b64decode(
                            readme_data["content"]
                        ).decode("utf-8")
                        # logger.info(
                        #     f"Successfully fetched README.md for {self.owner}/{self.repo}: {readme_content}"
                        # )
                    else:
                        logger.error(
                            f"Could not fetch README.md, status: {readme_response.status_code}"
                        )

                except Exception as e:
                    traceback.print_exc()
                    logger.info(
                        f"Could not fetch README.md, continuing with empty README: {e}"
                    )

            # Now determine the wiki structure
            await self.determine_wiki_structure(
                file_tree_data, readme_content, update_task_status, task_id
            )

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error fetching repository structure: {e}")
            self.error = str(e) if e else "An unknown error occurred"
            raise Exception(self.error)
        finally:
            self.request_in_progress = False

    async def determine_wiki_structure(
        self,
        file_tree_data: str,
        readme_content: str,
        update_task_status: Callable,
        task_id: str,
    ):

        # instruction for creating either comprehensive or concise wiki structure
        try:
            update_task_status(task_id, "processing", "Determining wiki structure...")
            # Define XML structure templates
            comprehensive_xml_format = """
<wiki_structure>
  <title>[Overall title for the wiki]</title>
  <description>[Brief description of the repository]</description>
  <sections>
    <section id="section-1">
      <title>[Section title]</title>
      <pages>
        <page_ref>page-1</page_ref>
        <page_ref>page-2</page_ref>
      </pages>
      <subsections>
        <section_ref>section-2</section_ref>
      </subsections>
    </section>
    <!-- More sections as needed -->
  </sections>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[Path to a relevant file]</file_path>
        <!-- More file paths as needed -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- More related page IDs as needed -->
      </related_pages>
      <parent_section>section-1</parent_section>
    </page>
    <!-- More pages as needed -->
  </pages>
</wiki_structure>"""
            concise_xml_format = """
<wiki_structure>
  <title>[Overall title for the wiki]</title>
  <description>[Brief description of the repository]</description>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[Path to a relevant file]</file_path>
        <!-- More file paths as needed -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- More related page IDs as needed -->
      </related_pages>
    </page>
    <!-- More pages as needed -->
  </pages>
</wiki_structure>"""

            xml_format_to_use = comprehensive_xml_format
            page_count_instruction = "8-12"
            view_type_instruction = "comprehensive"
            sections_guidance = """
Create a structured wiki with the following main sections:
- Overview (general information about the project)
- System Architecture (how the system is designed)
- Core Features (key functionality)
- Data Management/Flow: If applicable, how data is stored, processed, accessed, and managed (e.g., database schema, data pipelines, state management).
- Frontend Components (UI elements, if applicable.)
- Backend Systems (server-side components)
- Model Integration (AI model connections)
- Deployment/Infrastructure (how to deploy, what's the infrastructure like)
- Extensibility and Customization: If the project architecture supports it, explain how to extend or customize its functionality (e.g., plugins, theming, custom modules, hooks).

Each section should contain relevant pages. For example, the "Frontend Components" section might include pages for "Home Page", "Repository Wiki Page", "Ask Component", etc.
"""
            content_message = f"""
Analyze this GitHub repository ${self.owner}/${self.repo} and create a wiki structure for it.

1. The complete file tree of the project:
<file_tree>
{file_tree_data}
</file_tree>

2. The README file of the project:
<readme>
{readme_content}
</readme>

I want to create a wiki for this repository. Determine the most logical structure for a wiki based on the repository's content.

IMPORTANT: The wiki content will be generated in English language.

When designing the wiki structure, include pages that would benefit from visual diagrams, such as:
- Architecture overviews
- Data flow descriptions
- Component relationships
- Process workflows
- State machines
- Class hierarchies

{sections_guidance}

Return your analysis in the following XML format:

{xml_format_to_use}

IMPORTANT FORMATTING INSTRUCTIONS:
- Return ONLY the valid XML structure specified above
- DO NOT wrap the XML in markdown code blocks (no \`\`\` or \`\`\`xml)
- DO NOT include any explanation text before or after the XML
- Ensure the XML is properly formatted and valid
- Start directly with <wiki_structure> and end with </wiki_structure>

IMPORTANT:
1. Create {page_count_instruction} pages that would make a {view_type_instruction} wiki for this repository
2. Each page should focus on a specific aspect of the codebase (e.g., architecture, key features, setup)
3. The relevant_files should be actual files from the repository that would be used to generate that page
4. Return ONLY valid XML with the structure specified above, with no markdown code block delimiters
"""
            request_body = {
                "type": self.repo_info["type"],
                "messages": [{"role": "user", "content": content_message}],
                "repo_url": self.repo_url,
                "model": "gemini-2.5-pro",
            }
            ws_base_url = TARGET_SERVER_BASE_URL.replace("http", "ws", 1)
            ws_url = f"{ws_base_url}/ws/chat"
            http_api_url = f"{TARGET_SERVER_BASE_URL}/api/chat/stream"

            try:
                # Try websocket connection first
                async with await asyncio.wait_for(
                    websockets.connect(ws_url), timeout=5
                ) as ws:
                    logger.info("WebSocket connection established for wiki structure")
                    await ws.send(json.dumps(request_body))

                    messages_parts = []
                    async for message in ws:
                        messages_parts.append(str(message))
                    response_text = "".join(messages_parts)
                    logger.info("Received response from WebSocket")
            except Exception as e:
                logger.error(f"WebSocket error: {e}, falling back to HTTP API")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        http_api_url,
                        json=request_body,
                        headers={"Content-Type": "application/json"},
                        timeout=90,
                    )
                    response.raise_for_status()
                    response_text = response.text

            # Clean up markdown delimiters
            response_text = re.sub(
                r"^```(?:xml)?\s*",
                "",
                response_text,
                flags=re.IGNORECASE | re.MULTILINE,
            )
            response_text = re.sub(
                r"```\s*$", "", response_text, flags=re.IGNORECASE | re.MULTILINE
            )

            xml_match = re.search(
                r"<wiki_structure>[\s\S]*?<\/wiki_structure>",
                response_text,
                re.MULTILINE,
            )
            if not xml_match:
                raise ValueError(
                    "No valid <wiki_structure> XML found in the response. "
                )

            xml_text = xml_match.group(0)
            xml_text = re.sub(
                r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", xml_text
            )  # Remove control chars

            # Parse the XML to ensure it's valid
            try:
                xml_root = ET.fromstring(xml_text)
            except ET.ParseError as e:
                raise ValueError(
                    f"Invalid XML structure returned: {e}. Response was: {response_text}"
                )

            title = xml_root.findtext("title", default="")
            description = xml_root.findtext("description", default="")

            parsed_pages_list: List[WikiPage] = []
            page_elements = xml_root.findall("pages/page")

            for i, page_elem in enumerate(page_elements):
                page_id = page_elem.get("id", f"page-{i + 1}")
                page_title = page_elem.findtext("title", default="").strip()
                page_description = page_elem.findtext("description", default="").strip()
                importance_text = (
                    page_elem.findtext("importance", default="medium").strip().lower()
                )
                importance = (
                    importance_text
                    if importance_text in ["high", "medium", "low"]
                    else "medium"
                )
                file_paths: List[str] = []
                for file_elem in page_elem.findall("relevant_files/file_path"):
                    if file_elem.text:
                        file_paths.append(file_elem.text.strip())

                related_pages_ids: List[str] = []
                for related_elem in page_elem.findall("related_pages/related"):
                    if related_elem.text:
                        related_pages_ids.append(related_elem.text.strip())

                parent_section = page_elem.findtext("parent_section", default="")

                parsed_page = WikiPage(
                    id=page_id,
                    title=page_title,
                    description=page_description,
                    file_paths=file_paths,
                    importance=importance,
                    related_pages=related_pages_ids,
                    parent_section=parent_section,
                )
                parsed_pages_list.append(parsed_page)
            logger.info(f"Parsed {len(parsed_pages_list)} pages from XML")

            parsed_sections_list: List[WikiSection] = []
            root_section_ids_list: List[str] = []

            all_section_ids_in_xml = set()
            section_elements = xml_root.findall("sections/section")
            # Collect all section IDs first
            for section_elem in section_elements:
                section_id = section_elem.get("id", "")
                if section_id:
                    all_section_ids_in_xml.add(section_id)

            referenced_as_subsection_ids = set()
            for i, section_elem in enumerate(section_elements):
                section_id = section_elem.get("id", f"section-{i + 1}")
                section_title = section_elem.findtext("title", default="").strip()
                page_refs: List[str] = [
                    page_ref.text.strip()
                    for page_ref in section_elem.findall("pages/page_ref")
                    if page_ref.text
                ]
                subsection_refs: List[str] = []

                for subsection_ref in section_elem.findall("subsections/section_ref"):
                    if subsection_ref.text:
                        subsection_id = subsection_ref.text.strip()
                        subsection_refs.append(subsection_id)
                        referenced_as_subsection_ids.add(subsection_id)

                section_data = WikiSection(
                    id=section_id,
                    title=section_title,
                    pages=page_refs,
                    subsections=subsection_refs if subsection_refs else None,
                )
                parsed_sections_list.append(section_data)

            root_section_ids_list = list(
                all_section_ids_in_xml - referenced_as_subsection_ids
            )
            self.wiki_structure = WikiStructure(
                id="wiki",
                title=title,
                description=description,
                pages=parsed_pages_list,
                sections=parsed_sections_list,
                rootSections=root_section_ids_list,
            )
            update_task_status(
                task_id,
                "processing",
                "Wiki structure determined successfully.",
                WikiCacheData(
                    wiki_structure=WikiStructureModel.model_validate(
                        asdict(self.wiki_structure)
                    ),
                    generated_pages={},
                ),
            )

            logger.info(
                f"Wiki structure determined successfully. Title: {title}, "
                f"Pages: {len(parsed_pages_list)}, "
                f"Sections: {len(parsed_sections_list)}, Root Sections: {len(root_section_ids_list)}"
            )
            # Start generating content for all pages with controlled concurrency
            if parsed_pages_list:
                self.pages_in_progress = {page.id for page in parsed_pages_list}
                logger.info(
                    f"Starting content generation for {len(parsed_pages_list)} pages. Concurrency limit: 1"
                )

                page_queue = asyncio.Queue()
                for page_to_generate in parsed_pages_list:
                    await page_queue.put(page_to_generate)

                worker_tasks = []
                for i in range(1):
                    worker_task = asyncio.create_task(
                        self._generate_page_content_for_structure(
                            page_queue, update_task_status, task_id
                        )
                    )
                    worker_tasks.append(worker_task)

                await page_queue.join()

                for task in worker_tasks:
                    task.cancel()

                await asyncio.gather(*worker_tasks, return_exceptions=True)

                logger.info(
                    f"Content generation completed for {len(self.generated_pages)} pages."
                )

            data_to_cache = {
                "owner": self.owner,
                "repo": self.repo,
                "repo_type": self.repo_info["type"],
                "wiki_structure": asdict(self.wiki_structure),
                "generated_pages": {
                    page.id: asdict(page) for page in parsed_pages_list
                },
            }
            await self._save_wiki_data_to_cache(data_to_cache)

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error determining wiki structure: {e}")
            self.error = str(e) if e else "An unknown error occurred"
            return

    async def _generate_page_content_for_structure(
        self, queue: asyncio.Queue, update_task_status: Callable, task_id: str
    ):
        while True:
            try:
                page_data: WikiPage = await queue.get()
                try:
                    await self._generate_page_content(
                        page_data, update_task_status, task_id
                    )
                except Exception as e:
                    traceback.print_exc()
                    if page_data.id in self.pages_in_progress:
                        self.pages_in_progress.remove(page_data.id)
                        logger.error(
                            f"Error generating content for page {page_data.id} - {page_data.title}: {e}"
                        )
                finally:
                    queue.task_done()
            except asyncio.CancelledError:
                logger.info("Page content generation worker cancelled, exiting.")
                break
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error in page content generation worker: {e}")
                break

    async def _generate_page_content(
        self, page_data: WikiPage, update_task_status: Callable, task_id: str
    ):
        update_task_status(
            task_id,
            "processing",
            f"Generating content for {page_data.title}.",
            WikiCacheData(
                wiki_structure=WikiStructureModel.model_validate(
                    asdict(self.wiki_structure)
                ),
                generated_pages={},
            ),
            list(self.pages_in_progress),
        )

        page_id = page_data.id
        page_title = page_data.title
        try:
            file_paths = page_data.file_paths
            repo_url = self.repo_url
            file_paths_md_list = (
                "\n".join([f"- [{file_path}]({file_path})" for file_path in file_paths])
                if file_paths
                else "No specific files were pre-selected. You MUST find at least 5 relevant files from the codebase."
            )
            prompt_content = f"""
You are an expert technical writer and software architect.
Your task is to generate a comprehensive and accurate technical wiki page in Markdown format about a specific feature, system, or module within a given software project.

You will be given:
1. The "[WIKI_PAGE_TOPIC]" for the page you need to create.
2. A list of "[RELEVANT_SOURCE_FILES]" from the project that you MUST use as the sole basis for the content. You have access to the full content of these files. You MUST use AT LEAST 5 relevant source files for comprehensive coverage - if fewer are provided, search for additional related files in the codebase.

CRITICAL STARTING INSTRUCTION:
The very first thing on the page MUST be a `<details>` block listing ALL the `[RELEVANT_SOURCE_FILES]` you used to generate the content. There MUST be AT LEAST 5 source files listed - if fewer were provided, you MUST find additional related files to include.
Format it exactly like this:
<details>
<summary>Relevant source files</summary>

Remember, do not provide any acknowledgements, disclaimers, apologies, or any other preface before the `<details>` block. JUST START with the `<details>` block.
The following files were used as context for generating this wiki page:

{file_paths_md_list}
<!-- Add additional relevant files if fewer than 5 were provided, or if no files were initially provided. -->
</details>

Immediately after the `<details>` block, the main title of the page should be a H1 Markdown heading: `# {page_title}`.

Based ONLY on the content of the `[RELEVANT_SOURCE_FILES]`:

1.  **Introduction:** Start with a concise introduction (1-2 paragraphs) explaining the purpose, scope, and high-level overview of "{page_title}" within the context of the overall project. If relevant, and if information is available in the provided files, link to other potential wiki pages using the format `[Link Text](#page-anchor-or-id)`.

2.  **Detailed Sections:** Break down "{page_title}" into logical sections using H2 (`##`) and H3 (`###`) Markdown headings. For each section:
    *   Explain the architecture, components, data flow, or logic relevant to the section's focus, as evidenced in the source files.
    *   Identify key functions, classes, data structures, API endpoints, or configuration elements pertinent to that section.

3.  **Mermaid Diagrams:**
    *   EXTENSIVELY use Mermaid diagrams (e.g., `flowchart TD`, `sequenceDiagram`, `classDiagram`, `erDiagram`, `graph TD`) to visually represent architectures, flows, relationships, and schemas found in the source files.
    *   Ensure diagrams are accurate and directly derived from information in the `[RELEVANT_SOURCE_FILES]`.
    *   Provide a brief explanation before or after each diagram to give context.
    *   CRITICAL: All diagrams MUST follow strict vertical orientation:
       - Use "graph TD" (top-down) directive for flow diagrams
       - NEVER use "graph LR" (left-right)
       - Maximum node width should be 3-4 words
       - For sequence diagrams:
         - Start with "sequenceDiagram" directive on its own line
         - Define ALL participants at the beginning
         - Use descriptive but concise participant names
         - Use the correct arrow types:
           - ->> for request/asynchronous messages
           - -->> for response messages
           - -x for failed messages
         - Include activation boxes using +/- notation
         - Add notes for clarification using "Note over" or "Note right of"

4.  **Tables:**
    *   Use Markdown tables to summarize information such as:
        *   Key features or components and their descriptions.
        *   API endpoint parameters, types, and descriptions.
        *   Configuration options, their types, and default values.
        *   Data model fields, types, constraints, and descriptions.

5.  **Code Snippets:**
    *   Include short, relevant code snippets (e.g., Python, Java, JavaScript, SQL, JSON, YAML) directly from the `[RELEVANT_SOURCE_FILES]` to illustrate key implementation details, data structures, or configurations.
    *   Ensure snippets are well-formatted within Markdown code blocks with appropriate language identifiers.

6.  **Source Citations (EXTREMELY IMPORTANT):**
    *   For EVERY piece of significant information, explanation, diagram, table entry, or code snippet, you MUST cite the specific source file(s) and relevant line numbers from which the information was derived.
    *   Place citations at the end of the paragraph, under the diagram/table, or after the code snippet.
    *   Use the exact format: `Sources: [filename.ext:start_line-end_line]()` for a range, or `Sources: [filename.ext:line_number]()` for a single line. Multiple files can be cited: `Sources: [file1.ext:1-10](), [file2.ext:5](), [dir/file3.ext]()` (if the whole file is relevant and line numbers are not applicable or too broad).
    *   If an entire section is overwhelmingly based on one or two files, you can cite them under the section heading in addition to more specific citations within the section.
    *   IMPORTANT: You MUST cite AT LEAST 5 different source files throughout the wiki page to ensure comprehensive coverage.

7.  **Technical Accuracy:** All information must be derived SOLELY from the `[RELEVANT_SOURCE_FILES]`. Do not infer, invent, or use external knowledge about similar systems or common practices unless it's directly supported by the provided code. If information is not present in the provided files, do not include it or explicitly state its absence if crucial to the topic.

8.  **Clarity and Conciseness:** Use clear, professional, and concise technical language suitable for other developers working on or learning about the project. Avoid unnecessary jargon, but use correct technical terms where appropriate.

9.  **Conclusion/Summary:** End with a brief summary paragraph if appropriate for "{page_title}", reiterating the key aspects covered and their significance within the project.

IMPORTANT: Generate the content in English language.

Remember:
- Ground every claim in the provided source files.
- Prioritize accuracy and direct representation of the code's functionality and structure.
- Structure the document logically for easy understanding by other developers.
"""
            request_body = {
                "repo_url": repo_url,
                "type": self.repo_info["type"],
                "messages": [{"role": "user", "content": prompt_content}],
                "model": "gemini-2.5-pro",
            }
            ws_base_url = TARGET_SERVER_BASE_URL.replace("http", "ws", 1)
            ws_url = f"{ws_base_url}/ws/chat"
            http_api_url = f"{TARGET_SERVER_BASE_URL}/api/chat/stream"

            try:
                # Try websocket connection first
                async with await asyncio.wait_for(
                    websockets.connect(ws_url), timeout=5
                ) as ws:
                    logger.info(
                        f"WebSocket connection established for page: {page_title}"
                    )
                    await ws.send(json.dumps(request_body))

                    messages_parts = []
                    async for message in ws:
                        messages_parts.append(str(message))
                    response_text = "".join(messages_parts)
                    logger.info("Received response from WebSocket")
            except Exception as e:
                logger.error(f"WebSocket error: {e}, falling back to HTTP API")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        http_api_url,
                        json=request_body,
                        headers={"Content-Type": "application/json"},
                        timeout=90,
                    )
                    response.raise_for_status()
                    response_text = response.text

            cleaned_content = response_text.strip()
            logger.info(
                f"Cleaned content for page {page_id} - {page_title}: {cleaned_content[:50]}..."
            )
            page_data.content = cleaned_content

        except Exception as e:
            traceback.print_exc()
            logger.error(
                f"Error generating content for page {page_id} - {page_title}: {e}"
            )
        finally:
            if page_id in self.pages_in_progress:
                self.pages_in_progress.remove(page_id)
                logger.info(
                    f"Finished generating content for page {page_id} - {page_title}"
                )

    async def _save_wiki_data_to_cache(self, data_to_cache):
        try:
            cache_url = f"{TARGET_SERVER_BASE_URL}/api/wiki_cache"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    cache_url,
                    json=data_to_cache,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                response.raise_for_status()
                logger.info("Wiki data successfully saved to cache.")
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error saving wiki data to cache: {e}")
