# LLMs for Science Backend

[![Docker](https://github.com/Study-Project-AI-for-Science/backend/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Study-Project-AI-for-Science/backend/actions/workflows/docker-publish.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A full-stack research paper processing application built with Nuxt 3, designed to help scientists analyze and work with academic papers using Large Language Models (LLMs). The application processes PDF papers, extracts content, generates embeddings, and provides AI-powered analysis.

## ✨ Features

- 📄 **PDF Processing**: Upload and extract text from research papers
- 🤖 **AI-Powered Analysis**: Leverage local LLMs via Ollama for paper analysis
- 🔍 **Semantic Search**: Vector embeddings with pgvector for intelligent paper search
- 📚 **ArXiv Integration**: Fetch papers directly from ArXiv
- 📖 **LaTeX Parsing**: Extract references and citations from LaTeX sources
- 🔐 **Authentication**: Secure user authentication with Nuxt Auth Utils
- 🎨 **Modern UI**: Built with Vue 3, TailwindCSS 4.x, and TypeScript

## 🏗️ Tech Stack

### Frontend
- **Nuxt 3** - Full-stack Vue.js framework
- **Vue 3** with Composition API
- **TypeScript** throughout
- **TailwindCSS 4.x** for styling

### Backend
- **Nuxt Server API** - File-based routing
- **Drizzle ORM** - Type-safe database operations
- **PostgreSQL** with pgvector extension
- **S3-compatible storage** (MinIO/AWS S3)

### AI/ML
- **Ollama** for local LLM inference
- **PDF processing** with unpdf and pdfjs-dist
- **Vector embeddings** for semantic search
- **LaTeX parsing** capabilities

### Development Tools
- **Bun** - Fast package manager and runtime
- **Docker** - Containerized services
- **uv** - Python dependency management
- **Prettier** - Code formatting

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- [Docker](https://docs.docker.com/engine/install/) - For running PostgreSQL and MinIO
- [Bun](https://bun.sh/docs/installation) - JavaScript runtime and package manager
- [uv](https://docs.astral.sh/uv/) - Python package manager
  - Mac/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- [Pandoc](https://pandoc.org/installing.html) - Document converter (on Mac: `brew install pandoc`)
- [Ollama](https://ollama.ai/) - For running local LLMs (optional, but required for AI features)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Study-Project-AI-for-Science/backend.git
cd backend
```

### 2. Install Dependencies

```bash
bun install
```

### 3. Set Up Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and update the values as needed. The default values work for local development.

### 4. Start Services and Run Application

The setup script will start Docker services (PostgreSQL and MinIO), run database migrations, and start the development server:

**Mac/Linux:**
```bash
chmod +x ./scripts/setup.sh && bun run setup
```

**Windows:**
```bash
bun run setup
```

The application will be available at `http://localhost:3000`

## 🔧️ Development

### Project Structure

```
.
├── app/                    # Frontend Vue components and pages
│   ├── components/        # Reusable Vue components
│   ├── layouts/          # Page layouts
│   ├── pages/            # Application pages/routes
│   └── middleware/       # Route middleware
├── server/                # Backend API
│   ├── api/              # API endpoints
│   └── utils/            # Server utilities
├── packages/              # Shared packages
│   ├── database/         # Database schema and utilities
│   ├── ollama/           # Ollama LLM integration
│   ├── arxiv/            # ArXiv API integration
│   └── latex/            # LaTeX processing
├── modules/               # Python processing modules
│   ├── latex_parser/     # LaTeX reference parser
│   ├── ollama/           # Python Ollama utilities
│   └── retriever/        # Document retrieval
├── scripts/              # Setup and utility scripts
└── docker-compose.yaml   # Docker services configuration
```

### Available Scripts

```bash
# Development
bun run dev              # Start development server
bun run build            # Build for production
bun run preview          # Preview production build

# Database
bun run db:generate      # Generate database migrations
bun run db:migrate       # Run database migrations

# Code Quality
bun run pretty           # Format code with Prettier
uv run ruff check --fix  # Lint Python code
uv run ruff format       # Format Python code

# Testing
uv run pytest            # Run Python tests
```

### Database Management

#### Reset Database

If you need to start with a fresh database:

1. Stop Docker containers:
   ```bash
   docker compose down
   ```

2. Remove volumes (optional, for complete reset):
   ```bash
   docker compose down -v
   ```

3. Restart services:
   ```bash
   bun run setup
   ```

### Working with Ollama

To use the AI features, you need to have Ollama running with the required models:

```bash
# Start Ollama (if not already running)
ollama serve

# Pull required models
ollama pull gemma3:4b              # Chat model
ollama pull mxbai-embed-large      # Embedding model
```

Update the Ollama configuration in your `.env` file if using a remote instance.

### Python Development

The project uses `uv` for Python dependency management:

```bash
# Add a dependency
uv add package-name

# Remove a dependency
uv remove package-name

# Run a Python script
uv run python script.py

# Run tests
uv run pytest
```

## 🏛️ Architecture

The application follows a monorepo structure with clear separation of concerns:

- **Frontend**: Vue 3 + Nuxt 3 with server-side rendering
- **API Layer**: Nuxt server routes with RESTful design
- **Database**: PostgreSQL with pgvector for embeddings
- **Storage**: S3-compatible object storage for PDFs
- **AI Processing**: Ollama for LLM inference and embeddings
- **Python Modules**: Heavy processing tasks (LaTeX parsing, PDF extraction)

### Key Design Patterns

- **File-based routing** for API endpoints
- **Composable-based** state management
- **Type-safe** database operations with Drizzle ORM
- **Vector similarity search** for semantic paper retrieval
- **Event-driven** API handlers

## 🔌 API Documentation

API endpoints are available in the `server/api/` directory. Key endpoints include:

- `GET /api/papers` - List all papers
- `POST /api/papers` - Upload a new paper
- `GET /api/papers/:id` - Get paper details
- `POST /api/login` - User login
- `POST /api/register` - User registration

For detailed API documentation, see [API Documentation](http://localhost:3000/api/docs) when running the server.

## 🐳 Docker Deployment

Build and run with Docker:

```bash
# Build the image
docker build -t llms-for-science-backend .

# Run with docker-compose (includes all services)
docker compose up -d
```

The Dockerfile uses a multi-stage build for optimized production images.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for detailed information on how to contribute to this project.

Quick summary:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and commit: `git commit -m 'Add amazing feature'`
4. **Push to your fork**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines

- Follow the existing code style (Prettier for JS/TS, Ruff for Python)
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

For more details, see [CONTRIBUTING.md](CONTRIBUTING.md).

## 🐛 Troubleshooting

### Common Issues

**Docker containers won't start:**
- Ensure Docker daemon is running
- Check if ports 5432 (PostgreSQL), 9000/9001 (MinIO) are available
- Try `docker compose down && docker compose up -d`

**Database connection errors:**
- Verify PostgreSQL is running: `docker ps`
- Check `POSTGRES_URL` in `.env` file
- Ensure migrations have run: `bun run db:migrate`

**Ollama not working:**
- Verify Ollama is running: `curl http://localhost:11434`
- Check if models are downloaded: `ollama list`
- Verify `OLLAMA_HOST` in `.env` file

**Build errors:**
- Clear node_modules: `rm -rf node_modules && bun install`
- Clear Bun cache: `bun pm cache rm`

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Nuxt 3](https://nuxt.com/)
- Powered by [Ollama](https://ollama.ai/)
- Database by [PostgreSQL](https://www.postgresql.org/) and [pgvector](https://github.com/pgvector/pgvector)
- Styled with [TailwindCSS](https://tailwindcss.com/)

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

Made with ❤️ by the LLMs for Science team
