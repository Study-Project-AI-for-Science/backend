# LaTeX Reference Parser

A Python module for extracting bibliographic references from ArXiv paper sources. This parser can handle both BibTeX files and LaTeX files with \bibitem entries.

## Features

- Extract references from BibTeX (.bib) files
- Extract references from LaTeX (.tex) files with \bibitem entries
- Parse an entire paper directory to find all references
- Convert references to structured format with metadata fields
- Normalize LaTeX escape sequences
- Extract metadata such as authors, titles, journals, years, DOIs, URLs, etc.

## Installation

The reference parser is designed to be used as part of the LLMsForScience backend, but can also be used as a standalone module.

## Usage

### Basic Usage

```python
from latex_parser.reference_parser import extract_references

# Extract all references from a paper directory
references = extract_references('/path/to/paper/directory')
print(f"Found {len(references)} references")

# Access reference data
for ref in references:
    print(f"ID: {ref['id']}, Type: {ref['type']}")
    if 'author' in ref:
        print(f"Author: {ref['author']}")
    if 'title' in ref:
        print(f"Title: {ref['title']}")
```

### Advanced Usage

For more fine-grained control, use the `ReferenceParser` class directly:

```python
from latex_parser.reference_parser import ReferenceParser

# Create a parser instance
parser = ReferenceParser()

# Parse a specific BibTeX file
bibtex_entries = parser.parse_bibtex_file('/path/to/bibliography.bib')

# Parse a specific LaTeX file with bibliography
latex_entries = parser.parse_latex_bibliography('/path/to/paper.tex')

# Process entries
for entry in bibtex_entries:
    print(entry.id, entry.type)
    print(entry.get_field('author'))
    print(entry.get_field('title'))
```

### Command Line Usage

The parser can also be used from the command line:

```bash
# Extract references from a paper directory
python reference_parser.py /path/to/paper/directory

# Run tests with example papers
python test_reference_parser.py test_arxiv

# Test specific files
python test_reference_parser.py bibtex /path/to/file.bib
python test_reference_parser.py latex /path/to/file.tex
```

## Output Format

References are returned as a list of dictionaries, where each dictionary represents a reference with fields like:

```json
{
  "id": "smith2020example",
  "type": "article",
  "author": "Smith, John and Doe, Jane",
  "title": "An Example Paper",
  "journal": "Journal of Examples",
  "year": "2020",
  "volume": "42",
  "pages": "100-110",
  "doi": "10.1234/example.5678"
}
```

## Supported Fields

The parser attempts to extract as many fields as possible, including:

- Basic fields: author, title, year, journal/booktitle
- Publication details: volume, number, pages, publisher
- Identifiers: DOI, URL, arXiv ID
- Additional info: address, abstract, keywords, etc.

## Extensibility

The parser is designed to be extensible. You can add support for additional reference formats by extending the `ReferenceParser` class.

## Testing

Use the provided test script to verify functionality:

```bash
python test_reference_parser.py --help
```

## License

This project is part of the LLMsForScience backend.
