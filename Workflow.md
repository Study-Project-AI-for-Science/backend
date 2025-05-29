# [OUTDATED] LLMs for Science - Daily Development Workflow

This document provides a concise guide for the development workflow in this project. For initial setup instructions, please refer to the [README.md](README.md).

## Table of Contents

- [\[OUTDATED\] LLMs for Science - Daily Development Workflow](#outdated-llms-for-science---daily-development-workflow)
  - [Table of Contents](#table-of-contents)
  - [Running a singular file](#running-a-singular-file)
  - [Managing Dependencies](#managing-dependencies)
  - [Testing](#testing)
  - [Code formatting](#code-formatting)
  - [Code Organization](#code-organization)
  - [API Endpoints](#api-endpoints)
    - [Papers](#papers)
  - [Contributing](#contributing)
    - [Adding New Features](#adding-new-features)
  - [Remarks](#remarks)

## Running a singular file

- **Run using UV**: `uv run path_to_file/file_name.py`

## Managing Dependencies

- **Add a dependency**: `uv add package_name`
- **Remove a dependency**: `uv remove package_name`

## Testing

Run the full test suite:

```bash
uv run -m pytest
```

Run specific test files:

```bash
uv run -m pytest tests/test_database.py
```

## Code formatting

- **Format code**: `uv run ruff format`
- **Run linting**: `uv run ruff check --fix`

## Code Organization

- `app/` - Flask application and routes
- `modules/` - Core functionality modules
  - `database/` - Database interactions and migrations
  - `latex_parser/` - Tools for parsing LaTeX documents
  - `ollama/` - Integration with Ollama for embeddings and LLM tasks
  - `retriever/` - Paper retrieval from external sources (e.g., ArXiv)
  - `storage/` - S3 storage for PDFs and other files
- `scripts/` - Utility scripts for setup and maintenance
- `tests/` - Test suite

## API Endpoints

### Papers

- **Create a paper**: `POST /papers`
  - Upload PDF file, optionally provide title and authors
  - System extracts metadata, generates embeddings, and stores content
- **List all papers**: `GET /papers`
  - Returns all stored papers with their metadata
- **Get specific paper**: `GET /papers/{paper_id}`
  - Returns details of a specific paper
- **Update paper**: `PUT /papers/{paper_id}`
  - Update title, authors, abstract, etc.
- **Delete paper**: `DELETE /papers/{paper_id}`
  - Removes paper and its embeddings from the database
- **Get paper references**: `GET /papers/{paper_id}/references`
  - Returns all references for a specific paper

## Contributing

### Adding New Features

1. Create a new feature branch from Dev
2. Implement your changes
3. Add explaining comments and docstrings to the functions/files added
4. Add tests for new functionality
5. Run the test suite to ensure everything passes
6. Optional for bigger changes:
   To ensure it also works in normal usage
   1. Spin up the development backend as described in the Readme
   2. Do a few requests with differnt payloads to the endpoint(s) that your changes affect
7. Run the tests and fix either the test file, or your code, so that it works as intended
8. Run the formatting commands, and fix style problems
9. Commit your changes according the Github Guidelines in the workshops repository
10. On Github if you see the checks failing, please fix them, or contact @Antim8 for help
11. Submit a pull request and add @Antim8 as reviewer

## Remarks

If you have any questions regarding anything, have ideas for useful addition, or anything else, either propose a change using PR or hit up @Antim8
