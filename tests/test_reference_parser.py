#!/usr/bin/env python3
"""
Test module for reference_parser.py

This test suite verifies the functionality of the reference parser
for both BibTeX files and LaTeX files with \bibitem entries.
"""

import os
import pytest
from pathlib import Path

from modules.latex_parser.reference_parser import ReferenceParser, extract_references


class TestReferenceParser:
    """Test suite for ReferenceParser class."""

    @pytest.fixture
    def arxiv_root_dir(self):
        """Fixture that provides the path to ArXiv papers directory."""
        return Path("/Users/tpetersen/Dev/LLMsForScience/backend/modules/retriever/arxiv/Papers")

    @pytest.fixture
    def bibtex_paper_dir(self, arxiv_root_dir):
        """Fixture that provides the path to a paper with BibTeX file."""
        return arxiv_root_dir / "2410.20268v2.Centaur__a_foundation_model_of_human_cognition"

    @pytest.fixture
    def bibtex_file_path(self, bibtex_paper_dir):
        """Fixture that provides the path to a BibTeX file."""
        return bibtex_paper_dir / "sn-bibliography.bib"

    @pytest.fixture
    def latex_paper_dir(self, arxiv_root_dir):
        """Fixture that provides the path to a paper with LaTeX bibliography."""
        return arxiv_root_dir / "1706.03762v7.Attention_Is_All_You_Need"

    @pytest.fixture
    def latex_file_path(self, latex_paper_dir):
        """Fixture that provides the path to a LaTeX file with \bibitem entries."""
        return latex_paper_dir / "ms.tex"

    @pytest.fixture
    def reference_parser(self):
        """Fixture that provides a ReferenceParser instance."""
        return ReferenceParser()

    def test_bibtex_file_exists(self, bibtex_file_path):
        """Test that the BibTeX file exists in expected location."""
        assert bibtex_file_path.exists(), f"BibTeX test file not found at {bibtex_file_path}"

    def test_latex_file_exists(self, latex_file_path):
        """Test that the LaTeX file exists in expected location."""
        assert latex_file_path.exists(), f"LaTeX test file not found at {latex_file_path}"

    def test_parse_bibtex_file(self, reference_parser, bibtex_file_path):
        """Test parsing a BibTeX file."""
        entries = reference_parser.parse_bibtex_file(str(bibtex_file_path))

        # Check that entries were found
        assert len(entries) > 0, "No entries found in BibTeX file"

        # Check that some specific entries have expected fields
        for entry in entries:
            assert entry.id, "Entry ID is missing"
            assert entry.type, "Entry type is missing"

            # Most BibTeX entries should have these fields
            author = entry.get_field("author")
            title = entry.get_field("title")
            year = entry.get_field("year")

            # At least one of these fields should be present
            assert any([author, title, year]), "Entry is missing essential fields"

    def test_parse_latex_bibliography(self, reference_parser, latex_file_path):
        """Test parsing a LaTeX file with \bibitem entries."""
        entries = reference_parser.parse_latex_bibliography(str(latex_file_path))

        # Check that entries were found
        assert len(entries) > 0, "No entries found in LaTeX file"

        # Check that some specific entries have expected fields
        for entry in entries:
            assert entry.id, "Entry ID is missing"
            assert entry.type, "Entry type is missing"

            # Most bibitem entries should have these fields after parsing
            author = entry.get_field("author")
            title = entry.get_field("title")

            # At least one of these fields should be present
            assert any([author, title]), "Entry is missing essential fields"

            # Raw text should always be present
            assert entry.get_field("raw_text"), "Raw text is missing"

    def test_extract_references_bibtex(self, bibtex_paper_dir):
        """Test extract_references with a directory containing a BibTeX file."""
        references = extract_references(str(bibtex_paper_dir))

        # Check that references were found
        assert len(references) > 0, "No references found in paper directory"

        # Check structure of returned references
        for ref in references:
            assert "id" in ref, "Reference ID is missing"
            assert "type" in ref, "Reference type is missing"

            # Most should have these fields
            assert any(["author" in ref, "title" in ref]), "Reference is missing essential fields"

    def test_extract_references_latex(self, latex_paper_dir):
        """Test extract_references with a directory containing a LaTeX file with bibliography."""
        references = extract_references(str(latex_paper_dir))

        # Check that references were found
        assert len(references) > 0, "No references found in paper directory"

        # Check structure of returned references
        for ref in references:
            assert "id" in ref, "Reference ID is missing"
            assert "type" in ref, "Reference type is missing"

            # Most should have these fields
            assert any(["author" in ref, "title" in ref]), "Reference is missing essential fields"

    def test_reference_entry_to_dict(self, reference_parser, bibtex_file_path):
        """Test converting a ReferenceEntry to a dictionary."""
        entries = reference_parser.parse_bibtex_file(str(bibtex_file_path))
        assert len(entries) > 0, "No entries found for testing to_dict"

        # Convert the first entry to dict
        entry_dict = entries[0].to_dict()

        # Check dictionary structure
        assert isinstance(entry_dict, dict), "to_dict should return a dictionary"
        assert "id" in entry_dict, "Dictionary should contain id"
        assert "type" in entry_dict, "Dictionary should contain type"

        # Check that fields were transferred
        for field_name, field_value in entries[0].fields.items():
            assert field_name in entry_dict, f"Field {field_name} missing from dictionary"
            assert entry_dict[field_name] == field_value, f"Field {field_name} has incorrect value"

    def test_clean_bibtex_value(self, reference_parser):
        """Test cleaning of BibTeX field values."""
        test_cases = [
            (r"Title with \textbackslash{}", "Title with \\"),
            (r"Author with \"{a}", "Author with ä"),
            (r"Text with {braces}", "Text with braces"),
            (r"Multiple  spaces", "Multiple spaces"),
            (r"Math $\alpha + \beta$", "Math alpha + beta"),
        ]

        for input_value, expected_output in test_cases:
            cleaned = reference_parser._clean_bibtex_value(input_value)
            assert cleaned == expected_output, f"Clean failed for: {input_value}"

    @pytest.mark.skipif(
        not os.path.exists("/Users/tpetersen/Dev/LLMsForScience/backend/modules/retriever/arxiv/Papers"),
        reason="ArXiv paper directory not available",
    )
    def test_integration_both_formats(self, bibtex_paper_dir, latex_paper_dir):
        """Integration test using both formats."""
        bibtex_refs = extract_references(str(bibtex_paper_dir))
        latex_refs = extract_references(str(latex_paper_dir))

        assert len(bibtex_refs) > 0, "No references extracted from BibTeX paper"
        assert len(latex_refs) > 0, "No references extracted from LaTeX paper"

        # Check for possible common reference (e.g., 'vaswani2017attention' might be in both papers)
        bibtex_ids = {ref["id"].lower() for ref in bibtex_refs}
        latex_ids = {ref["id"].lower() for ref in latex_refs}

        # This is just informational and might not always pass depending on the papers
        common_ids = bibtex_ids.intersection(latex_ids)
        print(f"Common reference IDs between papers: {common_ids}")


if __name__ == "__main__":
    # For running tests manually
    pytest.main(["-xvs", __file__])
