"""Tests for utils module."""

import os
import tempfile
from standards_wiki.utils import slugify, utc_now_iso, ensure_parent


class TestSlugify:
    def test_simple_text(self):
        assert slugify("GB 7258-2017") == "gb-7258-2017"

    def test_chinese_text(self):
        # Chinese characters are preserved for UTF-8 filenames
        result = slugify("机动车运行安全技术条件")
        assert result == "机动车运行安全技术条件"

    def test_spaces_become_hyphens(self):
        assert slugify("hello world") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("hello   world") == "hello-world"

    def test_trailing_hyphens_stripped(self):
        assert slugify("  test  ") == "test"

    def test_uppercase_lowercased(self):
        assert slugify("ISO 26262") == "iso-26262"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_special_chars_replaced(self):
        assert slugify("GB/T 12345") == "gb-t-12345"


class TestUtcNowIso:
    def test_returns_iso_format(self):
        result = utc_now_iso()
        assert result.endswith("Z")
        # Should match ISO 8601 pattern
        assert len(result) == 20  # YYYY-MM-DDTHH:MM:SSZ

    def test_returns_string(self):
        assert isinstance(utc_now_iso(), str)


class TestEnsureParent:
    def test_creates_nested_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_path = os.path.join(tmpdir, "a", "b", "c", "file.txt")
            ensure_parent(deep_path)
            assert os.path.isdir(os.path.join(tmpdir, "a", "b", "c"))

    def test_no_op_if_parent_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ensure_parent(tmpdir)  # Should not raise
