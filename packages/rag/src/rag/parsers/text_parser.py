import re

from packages.rag.src.rag.parsers.base import ParsedDocument, ParsedSection


class TextParser:
    """Parses plain text and Markdown files, splitting on markdown headings."""

    HEADING_REGEX = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

    def parse(self, text: str, title: str = "Untitled Document") -> ParsedDocument:
        lines = text.splitlines()
        sections: list[ParsedSection] = []

        current_title = "Introduction"
        current_path = [title, "Introduction"]
        current_content_lines: list[str] = []

        for line in lines:
            heading_match = re.match(r"^(#{1,4})\s+(.+)$", line.strip())
            if heading_match:
                # Flush previous section
                content_str = "\n".join(current_content_lines).strip()
                if content_str:
                    sections.append(
                        ParsedSection(
                            title=current_title,
                            content=content_str,
                            section_path=" > ".join(current_path),
                            page_number=1,
                        )
                    )
                level = len(heading_match.group(1))
                new_title = heading_match.group(2).strip()
                current_title = new_title

                # Maintain hierarchical heading breadcrumbs
                if level == 1:
                    current_path = [title, new_title]
                else:
                    current_path = (
                        [title] + current_path[1 : min(level, len(current_path))] + [new_title]
                    )

                current_content_lines = []
            else:
                current_content_lines.append(line)

        # Flush final section
        final_content = "\n".join(current_content_lines).strip()
        if final_content:
            sections.append(
                ParsedSection(
                    title=current_title,
                    content=final_content,
                    section_path=" > ".join(current_path),
                    page_number=1,
                )
            )

        if not sections and text.strip():
            sections.append(
                ParsedSection(
                    title="General",
                    content=text.strip(),
                    section_path=f"{title} > General",
                    page_number=1,
                )
            )

        return ParsedDocument(
            title=title,
            file_type="text/markdown",
            sections=sections,
        )
