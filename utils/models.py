from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RepoInfo:
    owner: str
    repo: str
    type: str  # e.g., "github"


@dataclass
class WikiPage:
    id: str
    title: str
    description: str
    content: str = ""  # To be filled by generate_page_content_for_structure
    file_paths: List[str] = field(default_factory=list)
    importance: str = "medium"  # high|medium|low
    related_pages: List[str] = field(default_factory=list)
    parent_section: Optional[str] = None


@dataclass
class WikiSection:
    id: str
    title: str
    pages: List[str] = field(default_factory=list)  # List of page_ids
    subsections: Optional[List[str]] = field(
        default_factory=list
    )  # List of section_ids


@dataclass
class WikiStructure:
    id: str = "wiki"
    title: str = ""
    description: str = ""
    pages: List[WikiPage] = field(default_factory=list)
    sections: List[WikiSection] = field(default_factory=list)
    rootSections: List[str] = field(default_factory=list)
