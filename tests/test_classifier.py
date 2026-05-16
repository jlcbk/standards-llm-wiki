"""Tests for classifier module."""

import pytest

from standards_wiki.classifier import (
    classify_standard_type,
    classify_by_filename,
    classify_by_path,
)


class TestClassifyStandardType:
    # --- GB variants ---

    def test_gb_t(self):
        assert classify_standard_type("GB/T 12345-2024") == "gb-t"
        assert classify_standard_type("gb/t 12345") == "gb-t"
        assert classify_standard_type("GB/T12345") == "gb-t"

    def test_gb_z(self):
        assert classify_standard_type("GB/Z 20001-2019") == "gb-z"

    def test_gb_mandatory(self):
        assert classify_standard_type("GB 7258-2017") == "gb"
        assert classify_standard_type("GB 38031-2020") == "gb"

    def test_gb_in_long_title(self):
        assert classify_standard_type("GB 7258-2017 机动车运行安全技术条件") == "gb"

    # --- ISO ---

    def test_iso(self):
        assert classify_standard_type("ISO 26262:2018") == "iso"
        assert classify_standard_type("ISO 15118-2") == "iso"

    # --- IEC ---

    def test_iec(self):
        assert classify_standard_type("IEC 61851-1") == "iec"

    # --- SAE ---

    def test_sae(self):
        assert classify_standard_type("SAE J3016") == "sae"

    # --- ECE / UNECE ---

    def test_ece_regulation(self):
        assert classify_standard_type("ECE R100 Rev.3") == "ece"
        assert classify_standard_type("ECE R100") == "ece"

    def test_unece(self):
        assert classify_standard_type("UN ECE R100") == "unece"
        assert classify_standard_type("UNECE R100") == "unece"
        assert classify_standard_type("UN R100") == "unece"

    # --- Chinese policy / administrative ---

    def test_unknown_for_policy(self):
        # Policy notices don't match standard patterns
        result = classify_standard_type("工业和信息化部关于某事项的通知")
        assert result == "unknown"

    def test_unknown_for_generic(self):
        assert classify_standard_type("Some generic document") == "unknown"

    def test_unknown_for_empty(self):
        assert classify_standard_type("") == "unknown"

    # --- Priority: GB/T before GB ---

    def test_gb_t_takes_priority_over_gb(self):
        # GB/T should match before plain GB
        assert classify_standard_type("GB/T 7258") == "gb-t"
        assert classify_standard_type("GB/T 12345 机动车运行安全技术条件") == "gb-t"


class TestClassifyByFilename:
    def test_classifies_from_filename(self):
        assert classify_by_filename("gb-7258-2017.pdf") == "gb"
        assert classify_by_filename("iso-26262-2018.pdf") == "iso"

    def test_classifies_from_original_name(self):
        assert classify_by_filename("GB 7258-2017 机动车运行安全技术条件.pdf") == "gb"


class TestClassifyByPath:
    def test_classifies_from_path(self, tmp_path):
        pdf_path = tmp_path / "standards" / "gb-7258-2017.pdf"
        assert classify_by_path(pdf_path) == "gb"

    def test_classifies_from_string_path(self):
        assert classify_by_path("/raw/standards/iso-26262.pdf") == "iso"
