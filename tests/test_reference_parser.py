#!/usr/bin/env python3
"""
Test module for reference_parser.py

This test suite verifies the functionality of the reference parser
for both BibTeX files and LaTeX files with \bibitem entries.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, mock_open
from pathlib import Path

from modules.latex_parser.reference_parser import ReferenceParser, extract_references


class TestReferenceParser:
    """Test suite for ReferenceParser class."""

    @pytest.fixture
    def bibtex_content(self):
        """Fixture that provides sample BibTeX content for testing."""
        return """
@article{smith2020example,
  author = {Smith, John and Doe, Jane},
  title = {An Example Paper},
  journal = {Journal of Examples},
  year = {2020},
  volume = {42},
  number = {1},
  pages = {100--110},
  doi = {10.1234/example.5678}
}
@book{jones2019book,
  author = {Jones, Robert},
  title = {A Sample Book},
  publisher = {Academic Press},
  year = {2019},
  address = {New York, NY},
  isbn = {123-456-789}
}
@misc{brown2021tech,
  author = {Brown, Maria},
  title = {Technical Report on Examples},
  year = {2021},
  note = {Technical Report},
  institution = {Example University}
}
"""

    @pytest.fixture
    def latex_content(self):
        """Fixture that provides sample LaTeX bibliography content for testing."""
        return r"""
\begin{thebibliography}{99}
\bibitem{vaswani2017attention}
Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, and Illia Polosukhin.
\newblock Attention is all you need.
\newblock {\em Advances in Neural Information Processing Systems}, pages 5998--6008, 2017.

\bibitem{devlin2019bert}
Jacob Devlin, Ming-Wei Chang, Kenton Lee, and Kristina Toutanova.
\newblock BERT: Pre-training of deep bidirectional transformers for language understanding.
\newblock {\em arXiv preprint arXiv:1810.04805}, 2018.

\bibitem{kingma2014adam}
Diederik Kingma and Jimmy Ba.
\newblock Adam: A method for stochastic optimization.
\newblock In {\em ICLR}, 2015.
\end{thebibliography}
"""

    @pytest.fixture
    def temp_bibtex_file(self, bibtex_content):
        """Create a temporary BibTeX file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.bib', delete=False, mode='w+') as f:
            f.write(bibtex_content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def temp_latex_file(self, latex_content):
        """Create a temporary LaTeX file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.tex', delete=False, mode='w+') as f:
            f.write(latex_content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def temp_paper_dir(self, bibtex_content, latex_content):
        """Create a temporary directory with paper files for testing extract_references."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a BibTeX file
            bib_path = os.path.join(temp_dir, "references.bib")
            with open(bib_path, 'w') as f:
                f.write(bibtex_content)
            
            # Create a LaTeX file
            tex_path = os.path.join(temp_dir, "paper.tex")
            with open(tex_path, 'w') as f:
                f.write(latex_content)
            
            yield temp_dir

    @pytest.fixture
    def reference_parser(self):
        """Fixture that provides a ReferenceParser instance."""
        return ReferenceParser()

    def test_parse_bibtex_file(self, reference_parser, temp_bibtex_file):
        """Test parsing a BibTeX file."""
        entries = reference_parser.parse_bibtex_file(temp_bibtex_file)

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

    def test_parse_latex_bibliography(self, reference_parser, temp_latex_file):
        """Test parsing a LaTeX file with \bibitem entries."""
        entries = reference_parser.parse_latex_bibliography(temp_latex_file)

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

    def test_extract_references_bibtex(self, temp_paper_dir):
        """Test extract_references with a directory containing a BibTeX file."""
        references = extract_references(temp_paper_dir)

        # Check that references were found
        assert len(references) > 0, "No references found in paper directory"

        # Check structure of returned references
        for ref in references:
            assert "id" in ref, "Reference ID is missing"
            assert "type" in ref, "Reference type is missing"

            # Most should have these fields
            assert any(["author" in ref, "title" in ref]), "Reference is missing essential fields"

    def test_reference_entry_to_dict(self, reference_parser, temp_bibtex_file):
        """Test converting a ReferenceEntry to a dictionary."""
        entries = reference_parser.parse_bibtex_file(temp_bibtex_file)
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

    def test_integration_both_formats(self, temp_paper_dir):
        """Integration test using both formats."""
        references = extract_references(temp_paper_dir)
        
        assert len(references) > 0, "No references extracted from paper directory"

        # Check for specific references we expect to find
        reference_ids = {ref["id"].lower() for ref in references}
        expected_ids = {"smith2020example", "jones2019book", "brown2021tech", 
                      "vaswani2017attention", "devlin2019bert", "kingma2014adam"}
        
        # Check if at least some of our expected IDs are found
        assert any(ref_id in reference_ids for ref_id in expected_ids), \
            f"None of the expected reference IDs were found. Found: {reference_ids}"


if __name__ == "__main__":
    # For running tests manually
    pytest.main(["-xvs", __file__])
