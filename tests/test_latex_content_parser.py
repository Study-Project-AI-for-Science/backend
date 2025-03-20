import os
import pytest
from unittest.mock import patch, MagicMock
from modules.latex_parser.latex_content_parser import parse_latex_to_markdown, find_main_tex_file


class TestFindMainTexFile:
    """Tests for the find_main_tex_file function"""

    def test_find_main_tex_file_success(self, tmp_path):
        """Test finding the main LaTeX file in a directory successfully"""
        # Create a temporary TeX file with document environment
        main_tex_path = os.path.join(tmp_path, "main.tex")
        with open(main_tex_path, "w") as f:
            f.write(r"""
            \documentclass{article}
            \begin{document}
                Test content
            \end{document}
            """)

        # Create a second TeX file without document environment
        secondary_tex_path = os.path.join(tmp_path, "secondary.tex")
        with open(secondary_tex_path, "w") as f:
            f.write(r"""
            % This is just a helper file
            \newcommand{\helpercommand}{helper text}
            """)

        # Test the function
        result = find_main_tex_file(str(tmp_path))

        assert result is not None
        assert os.path.basename(result) == "main.tex"

    def test_find_main_tex_file_nested_directories(self, tmp_path):
        """Test finding the main LaTeX file in nested directories"""
        # Create a nested directory structure
        nested_dir = os.path.join(tmp_path, "nested", "subdirectory")
        os.makedirs(nested_dir)

        # Put the main TeX file in the nested directory
        main_tex_path = os.path.join(nested_dir, "main.tex")
        with open(main_tex_path, "w") as f:
            f.write(r"""
            \documentclass{article}
            \begin{document}
                Test content
            \end{document}
            """)

        # Test the function starting from the top directory
        result = find_main_tex_file(str(tmp_path))

        assert result is not None
        assert os.path.basename(result) == "main.tex"
        assert nested_dir in result

    def test_find_main_tex_file_not_found(self, tmp_path):
        """Test finding no main LaTeX file"""
        # Create a TeX file without document environment
        tex_path = os.path.join(tmp_path, "not_main.tex")
        with open(tex_path, "w") as f:
            f.write(r"""
            % This is just a helper file
            \newcommand{\helpercommand}{helper text}
            """)

        # Test the function
        result = find_main_tex_file(str(tmp_path))

        assert result is None

    def test_find_main_tex_file_unicode_error(self, tmp_path):
        """Test handling Unicode decode errors gracefully"""
        with patch("builtins.open", side_effect=[UnicodeDecodeError("utf-8", b"", 0, 1, "Test error")]):
            result = find_main_tex_file(str(tmp_path))
            assert result is None

    def test_find_main_tex_file_io_error(self, tmp_path):
        """Test handling IO errors gracefully"""
        with patch("builtins.open", side_effect=IOError("Test IO Error")):
            result = find_main_tex_file(str(tmp_path))
            assert result is None


class TestParseLatexToMarkdown:
    """Tests for the parse_latex_to_markdown function"""

    @patch("modules.latex_parser.latex_content_parser.pandoc")
    def test_parse_latex_to_markdown_file_success(self, mock_pandoc, tmp_path):
        """Test successful conversion of a LaTeX file to Markdown"""
        # Set up the mock to return expected markdown
        mock_doc = MagicMock()
        mock_pandoc.read.return_value = mock_doc
        mock_pandoc.write.return_value = "# Converted Markdown\n\nTest content"

        # Create a test LaTeX file
        test_file = os.path.join(tmp_path, "test.tex")
        with open(test_file, "w") as f:
            f.write(r"""
            \documentclass{article}
            \begin{document}
                \section{Test Section}
                Test content
            \end{document}
            """)

        # Call the function with the file path
        result = parse_latex_to_markdown(test_file)

        # Verify the result
        assert "# Converted Markdown" in result
        assert "Test content" in result

        # Verify pandoc was called correctly
        mock_pandoc.read.assert_called_once()
        mock_pandoc.write.assert_called_once_with(mock_doc, format="markdown")

    @patch("modules.latex_parser.latex_content_parser.find_main_tex_file")
    @patch("modules.latex_parser.latex_content_parser.pandoc")
    def test_parse_latex_to_markdown_directory_success(self, mock_pandoc, mock_find_file, tmp_path):
        """Test successful conversion from a directory containing LaTeX files"""
        # Set up mocks
        mock_find_file.return_value = os.path.join(tmp_path, "main.tex")
        mock_doc = MagicMock()
        mock_pandoc.read.return_value = mock_doc
        mock_pandoc.write.return_value = "# Converted from Directory\n\nTest content"

        # Create the test directory
        os.makedirs(tmp_path, exist_ok=True)

        # Call the function with the directory path
        result = parse_latex_to_markdown(str(tmp_path))

        # Verify the result
        assert "# Converted from Directory" in result
        assert "Test content" in result

        # Verify our mocks were called correctly
        mock_find_file.assert_called_once_with(str(tmp_path))
        mock_pandoc.read.assert_called_once()

    def test_parse_latex_to_markdown_file_not_found(self):
        """Test handling of a file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            parse_latex_to_markdown("/nonexistent/path/to/file.tex")

    @patch("modules.latex_parser.latex_content_parser.find_main_tex_file")
    def test_parse_latex_to_markdown_no_main_tex_in_dir(self, mock_find_file, tmp_path):
        """Test handling of a directory with no main TeX file"""
        # Set up mock to return None (no main file found)
        mock_find_file.return_value = None

        with pytest.raises(FileNotFoundError):
            parse_latex_to_markdown(str(tmp_path))

    @patch("modules.latex_parser.latex_content_parser.pandoc")
    def test_parse_latex_to_markdown_conversion_error(self, mock_pandoc, tmp_path):
        """Test handling of pandoc conversion errors"""
        # Create a test file
        test_file = os.path.join(tmp_path, "error.tex")
        with open(test_file, "w") as f:
            f.write(r"\documentclass{article}\begin{document}Test\end{document}")

        # Set up mock to raise an exception during conversion
        mock_pandoc.read.side_effect = Exception("Pandoc conversion error")

        # Test the function
        with pytest.raises(Exception, match="Pandoc conversion error"):
            parse_latex_to_markdown(test_file)

    @patch("os.chdir")
    def test_parse_latex_to_markdown_directory_change_error(self, mock_chdir, tmp_path):
        """Test handling of errors when changing directories"""
        # Create a test file
        test_file = os.path.join(tmp_path, "test.tex")
        with open(test_file, "w") as f:
            f.write(r"\documentclass{article}\begin{document}Test\end{document}")

        # Set up mock to raise an exception during directory change
        mock_chdir.side_effect = OSError("Permission denied")

        # Test the function
        with pytest.raises(OSError, match="Permission denied"):
            parse_latex_to_markdown(test_file)

    def test_parse_latex_to_markdown_cleanup(self, tmp_path):
        """Test that the original directory is restored even if errors occur"""
        # Create a test file
        test_file = os.path.join(tmp_path, "test.tex")
        with open(test_file, "w") as f:
            f.write(r"\documentclass{article}\begin{document}Test\end{document}")

        # Get the current directory before calling the function
        original_dir = os.getcwd()

        # Call with exception patched in
        with patch("modules.latex_parser.latex_content_parser.pandoc.read", side_effect=Exception("Test exception")):
            with pytest.raises(Exception, match="Test exception"):
                parse_latex_to_markdown(test_file)

        # Verify we're back in the original directory
        assert os.getcwd() == original_dir


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
