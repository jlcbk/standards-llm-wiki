"""Tests for HTML extractor."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from standards_wiki.extractors.html import extract_html, _collect_attachments


@pytest.fixture(autouse=True)
def mock_requests_get(tmp_path, monkeypatch):
    """Mock requests.get and isolate raw HTML snapshots."""
    monkeypatch.setattr("standards_wiki.archive._RAW_DIR", tmp_path / "raw")
    with patch("standards_wiki.extractors.html.requests.get") as mock_get:
        yield mock_get


class TestExtractHtml:
    def test_raises_on_connection_error(self, mock_requests_get, tmp_path):
        mock_requests_get.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            extract_html("https://example.com/doc.html", slug="test", output_base=tmp_path / "sources")

    def test_extracts_html_content(self, mock_requests_get, tmp_path):
        html = """<!DOCTYPE html>
<html>
<head><title>Test Document</title></head>
<body>
<h1>Main Title</h1>
<p>This is the main content paragraph.</p>
</body>
</html>"""
        mock_response = Mock()
        mock_response.text = html
        mock_response.url = "https://example.com/doc.html"
        mock_response.raise_for_status = lambda: None
        mock_requests_get.return_value = mock_response

        output_base = tmp_path / "sources"
        result = extract_html("https://example.com/doc.html", slug="test-doc", output_base=output_base)

        assert "Test Document" in result["title"]
        assert result["url"] == "https://example.com/doc.html"
        assert result["source_text"].endswith("test-doc.md")

    def test_writes_markdown_file(self, mock_requests_get, tmp_path):
        html = """<!DOCTYPE html>
<html>
<head><title>My Article</title></head>
<body>
<h1>Article Title</h1>
<p>Some article content here.</p>
</body>
</html>"""
        mock_response = Mock()
        mock_response.text = html
        mock_response.url = "https://example.com/article.html"
        mock_response.raise_for_status = lambda: None
        mock_requests_get.return_value = mock_response

        output_base = tmp_path / "sources"
        result = extract_html("https://example.com/article.html", slug="article", output_base=output_base)

        md_path = Path(result["source_text"])
        assert md_path.exists()
        content = md_path.read_text()
        assert "Article Title" in content
        assert "Source URL:" in content

    def test_saves_raw_html_snapshot(self, mock_requests_get, tmp_path):
        html = "<html><body><p>Test</p></body></html>"
        mock_response = Mock()
        mock_response.text = html
        mock_response.url = "https://example.com/test.html"
        mock_response.raise_for_status = lambda: None
        mock_requests_get.return_value = mock_response

        # Mock archive_html to use tmp_path
        with patch("standards_wiki.extractors.html.archive_html") as mock_archive:
            mock_archive.return_value = {
                "raw_path": str(tmp_path / "raw" / "web" / "test.html"),
                "sha256": "abc123",
            }

            output_base = tmp_path / "sources"
            result = extract_html("https://example.com/test.html", slug="test", output_base=output_base)

            assert result["sha256"] == "abc123"
            mock_archive.assert_called_once()

    def test_collects_attachments(self, mock_requests_get, tmp_path):
        html = """<!DOCTYPE html>
<html>
<body>
<a href="/docs/guide.pdf">Guide</a>
<a href="https://example.com/spec.docx">Spec</a>
<a href="/files/manual.doc">Manual</a>
<a href="/other.txt">Not an attachment</a>
</body>
</html>"""
        mock_response = Mock()
        mock_response.text = html
        mock_response.url = "https://example.com/page.html"
        mock_response.raise_for_status = lambda: None
        mock_requests_get.return_value = mock_response

        output_base = tmp_path / "sources"
        result = extract_html("https://example.com/page.html", slug="page", output_base=output_base)

        assert len(result["attachments"]) >= 2

    def test_follows_redirects(self, mock_requests_get, tmp_path):
        html = "<html><body><p>Redirected content</p></body></html>"
        mock_response = Mock()
        mock_response.text = html
        mock_response.url = "https://example.com/actual-location.html"
        mock_response.raise_for_status = lambda: None
        mock_requests_get.return_value = mock_response

        output_base = tmp_path / "sources"
        result = extract_html("https://example.com/redirected", slug="test", output_base=output_base)

        # Should use the final URL after redirect
        assert result["url"] == "https://example.com/actual-location.html"


class TestCollectAttachments:
    def test_collects_pdf_links(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a href="/doc.pdf">PDF</a><a href="https://x.com/a.pdf">Ext</a>', "html.parser")
        attachments = _collect_attachments(soup, base_url="https://example.com/page.html")
        assert len(attachments) == 2

    def test_collects_doc_links(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a href="/file.doc">DOC</a>', "html.parser")
        attachments = _collect_attachments(soup, base_url="https://example.com/page.html")
        assert len(attachments) == 1

    def test_collects_docx_links(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a href="/file.docx">DOCX</a>', "html.parser")
        attachments = _collect_attachments(soup, base_url="https://example.com/page.html")
        assert len(attachments) == 1

    def test_ignores_non_attachment_links(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a href="/page.html">HTML</a><a href="/style.css">CSS</a>', "html.parser")
        attachments = _collect_attachments(soup, base_url="https://example.com/page.html")
        assert len(attachments) == 0

    def test_deduplicates_attachments(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<a href="/same.pdf">A</a><a href="/same.pdf">B</a>', "html.parser")
        attachments = _collect_attachments(soup, base_url="https://example.com/page.html")
        assert len(attachments) == 1
