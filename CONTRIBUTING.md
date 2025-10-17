# Contributing to LLMs for Science Backend

Thank you for your interest in contributing to the LLMs for Science Backend project! We welcome contributions from the community and are grateful for your support.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## 📜 Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

### Our Standards

- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community and project
- Show empathy towards other community members

## 🚀 Getting Started

### Prerequisites

Before you start contributing, ensure you have completed the setup described in the [README.md](README.md):

1. Install required tools (Docker, Bun, uv, Pandoc)
2. Clone the repository
3. Install dependencies
4. Set up environment variables
5. Run the setup script

### Finding Issues to Work On

- Check the [Issues](https://github.com/Study-Project-AI-for-Science/backend/issues) page for open tasks
- Look for issues labeled `good first issue` for beginner-friendly tasks
- Issues labeled `help wanted` are great opportunities to contribute
- Feel free to propose new features or improvements

## 🔄 Development Workflow

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/backend.git
cd backend

# Add upstream remote
git remote add upstream https://github.com/Study-Project-AI-for-Science/backend.git
```

### 2. Create a Branch

Create a descriptive branch name for your work:

```bash
git checkout -b feature/add-new-feature
# or
git checkout -b fix/issue-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests

### 3. Make Your Changes

- Write clear, concise code that follows the project's coding standards
- Add tests for new functionality
- Update documentation as needed
- Commit your changes with meaningful commit messages

### 4. Keep Your Branch Updated

Regularly sync your branch with the upstream repository:

```bash
git fetch upstream
git rebase upstream/main
```

### 5. Test Your Changes

Before submitting, ensure all tests pass:

```bash
# Run TypeScript/JavaScript tests (if available)
bun run test

# Run Python tests
uv run pytest

# Lint your code
bun run pretty
uv run ruff check --fix
uv run ruff format

# Build the project
bun run build
```

## 📝 Submitting Changes

### Pull Request Process

1. **Push to Your Fork**
   ```bash
   git push origin feature/add-new-feature
   ```

2. **Open a Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill out the PR template with details about your changes

3. **PR Title and Description**
   - Use a clear, descriptive title
   - Reference related issues (e.g., "Fixes #123")
   - Describe what changes you made and why
   - Include screenshots for UI changes
   - List any breaking changes

4. **Code Review**
   - Address feedback from reviewers promptly
   - Make requested changes in new commits
   - Keep the discussion constructive and professional

5. **Merge**
   - Once approved, a maintainer will merge your PR
   - Your contribution will be included in the next release!

### Commit Message Guidelines

Write clear commit messages that explain what and why:

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

**Example:**
```
feat: Add semantic search for papers

Implemented vector similarity search using pgvector to enable
semantic search across research papers. Users can now find
papers based on meaning rather than just keywords.

Closes #42
```

## 💻 Coding Standards

### TypeScript/JavaScript

- Follow the Prettier configuration (`.prettierrc`)
- Use TypeScript for type safety
- Use meaningful variable and function names
- Add JSDoc comments for complex functions
- Follow Vue 3 Composition API patterns

```typescript
// Good
async function processPaper(paperId: string): Promise<Paper> {
  const paper = await db.query.papers.findFirst({
    where: eq(papers.id, paperId),
  })
  return paper
}

// Bad
async function proc(id: any) {
  return await db.query.papers.findFirst({ where: eq(papers.id, id) })
}
```

### Python

- Follow PEP 8 style guide
- Use Ruff for linting and formatting
- Add type hints for function parameters and return values
- Write docstrings for classes and functions

```python
# Good
def extract_references(paper_path: str) -> list[dict[str, str]]:
    """
    Extract bibliographic references from a paper directory.
    
    Args:
        paper_path: Path to the paper directory
        
    Returns:
        List of reference dictionaries with metadata
    """
    parser = ReferenceParser()
    return parser.extract_all(paper_path)

# Bad
def extract_refs(path):
    parser = ReferenceParser()
    return parser.extract_all(path)
```

### Database

- Use Drizzle ORM for all database operations
- Write migrations for schema changes
- Use prepared statements for queries
- Add proper indexes for performance

### API Design

- Follow RESTful conventions
- Use appropriate HTTP methods and status codes
- Validate input with Zod schemas
- Return consistent error responses
- Document endpoints clearly

## 🧪 Testing Guidelines

### Writing Tests

- Write tests for new features and bug fixes
- Aim for meaningful test coverage
- Use descriptive test names
- Test edge cases and error conditions

### Python Tests

```python
def test_extract_references():
    """Test reference extraction from BibTeX file"""
    parser = ReferenceParser()
    refs = parser.parse_bibtex_file("test.bib")
    assert len(refs) > 0
    assert refs[0].get_field("author") is not None
```

### Running Tests

```bash
# Python tests
uv run pytest

# TypeScript tests (if available)
bun run test
```

## 📚 Documentation

Good documentation is crucial for open-source projects:

- Update the README.md if you change setup/usage
- Add JSDoc/docstrings to your code
- Update API documentation for new endpoints
- Include examples in your documentation
- Keep the AGENTS.md file updated if you change the architecture

## 🤝 Community

### Getting Help

- **Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Pull Requests**: Review and comment on others' PRs

### Recognition

All contributors are valued and recognized:
- Your name will be added to the contributors list
- Significant contributions may be highlighted in release notes

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

## ❓ Questions?

If you have questions about contributing, feel free to:
- Open an issue with the `question` label
- Reach out to the maintainers

Thank you for making LLMs for Science Backend better! 🎉
