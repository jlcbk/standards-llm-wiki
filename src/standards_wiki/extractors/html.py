"""HTML extractor — fetch webpage and convert content to Markdown."""

import re
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

from ..archive import archive_html
from ..utils import ensure_parent

SourcesDir = Literal["standards", "regulations", "policies", "rules", "interpretations", "web"]

_DEFAULT_SOURCES_DIR = Path("sources")

# Extensions to look for as attachment links
_ATTACHMENT_EXTENSIONS = {".pdf", ".doc", ".docx"}


def extract_html(
    url: str,
    slug: str,
    sources_dir: SourcesDir = "web",
    output_base: Path | None = None,
    timeout: int = 30,
) -> dict:
    """Fetch a webpage and convert its content to Markdown.

    Args:
        url: The URL to fetch.
        slug: Slug for the output filename.
        sources_dir: Target subdirectory under sources/.
        output_base: Base directory for sources output (defaults to CWD/sources).
        timeout: Request timeout in seconds.

    Returns:
        dict with:
            - source_text: path to extracted Markdown file
            - raw_path: path to saved HTML snapshot
            - sha256: SHA256 hash of the HTML
            - attachments: list of attachment URLs found (.pdf, .doc, .docx)
            - title: page title if available
    """
    # Fetch the webpage
    response = requests.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()

    html_content = response.text
    actual_url = response.url  # Follow redirects

    # Save raw HTML snapshot
    archive_result = archive_html(html_content, slug=slug, source_url=actual_url)

    # Parse HTML and extract main content
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract title
    title = soup.title.string if soup.title else slug

    # Remove script, style, and other non-content elements
    for tag in soup.find_all(["script", "style", "noscript", "meta", "link", "head"]):
        tag.decompose()

    # Convert to Markdown
    md_text = markdownify(
        str(soup),
        heading_style="ATX",
        bullets="-",
        wrap=True,
        strip=["script", "style"],
    )

    # Collect attachment links
    attachments = _collect_attachments(soup, base_url=actual_url)

    # Write extracted Markdown to sources/
    base = output_base if output_base is not None else _DEFAULT_SOURCES_DIR
    target_dir = base / sources_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    output_filename = f"{slug}.md"
    output_path = target_dir / output_filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"<!-- Source URL: {actual_url} -->\n")
        f.write(f"<!-- Title: {title} -->\n")
        f.write(f"<!-- Extracted at: {__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} -->\n")
        if attachments:
            f.write(f"<!-- Attachments found: {len(attachments)} -->\n")
        f.write(f"\n# {title}\n\n")
        f.write(md_text)

    return {
        "source_text": str(output_path),
        "raw_path": archive_result["raw_path"],
        "sha256": archive_result["sha256"],
        "attachments": attachments,
        "title": title,
        "url": actual_url,
    }


def _collect_attachments(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Collect attachment links (.pdf, .doc, .docx) from the page."""
    attachments = []
    base = Path(base_url)

    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Check if it's an attachment by extension
        ext = Path(href).suffix.lower()
        if ext in _ATTACHMENT_EXTENSIONS:
            # Resolve relative URLs
            if href.startswith(("http://", "https://")):
                attachments.append(href)
            else:
                # Construct absolute URL
                attachments.append(str(base.parent / href.lstrip("/")))

    return sorted(set(attachments))
