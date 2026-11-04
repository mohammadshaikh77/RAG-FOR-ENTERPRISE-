from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedSection:
    """Represents a coherent section within a document."""

    title: str
    content: str
    section_path: str
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Normalized document representation output by all parsers."""

    title: str
    file_type: str
    sections: list[ParsedSection]
    metadata: dict[str, Any] = field(default_factory=dict)
