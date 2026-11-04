from bs4 import BeautifulSoup, Tag

from packages.rag.src.rag.parsers.base import ParsedDocument, ParsedSection


class HTMLParser:
    """Parses HTML documents into structured sections based on h1-h4 tags."""

    def parse(self, html_content: str, title: str = "Untitled Document") -> ParsedDocument:
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip scripts, styles, navigations
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        page_title = title
        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()

        sections: list[ParsedSection] = []
        current_title = "Overview"
        current_path = [page_title, "Overview"]
        current_text_blocks: list[str] = []

        elements = soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "table", "div"])

        for el in elements:
            if not isinstance(el, Tag):
                continue

            tag_name = el.name.lower()
            if tag_name in ["h1", "h2", "h3", "h4"]:
                # Flush previous section
                content_str = "\n".join(current_text_blocks).strip()
                if content_str:
                    sections.append(
                        ParsedSection(
                            title=current_title,
                            content=content_str,
                            section_path=" > ".join(current_path),
                            page_number=1,
                        )
                    )
                heading_text = el.get_text(separator=" ", strip=True)
                if heading_text:
                    current_title = heading_text
                    level = int(tag_name[1])
                    if level == 1:
                        current_path = [page_title, heading_text]
                    else:
                        current_path = (
                            [page_title]
                            + current_path[1 : min(level, len(current_path))]
                            + [heading_text]
                        )
                current_text_blocks = []
            elif tag_name in ["p", "ul", "ol", "table"]:
                text = el.get_text(separator=" ", strip=True)
                if text:
                    current_text_blocks.append(text)

        # Flush final section
        final_content = "\n".join(current_text_blocks).strip()
        if final_content:
            sections.append(
                ParsedSection(
                    title=current_title,
                    content=final_content,
                    section_path=" > ".join(current_path),
                    page_number=1,
                )
            )

        if not sections:
            full_text = soup.get_text(separator="\n", strip=True)
            if full_text:
                sections.append(
                    ParsedSection(
                        title="Body",
                        content=full_text,
                        section_path=f"{page_title} > Body",
                        page_number=1,
                    )
                )

        return ParsedDocument(
            title=page_title,
            file_type="text/html",
            sections=sections,
        )
