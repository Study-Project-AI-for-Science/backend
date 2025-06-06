# AI Agent Guide for LLMs for Science Backend

This guide is designed to help AI agents understand the structure, technologies, and patterns used in this repository.

## Repository Overview

This is a **full-stack research paper processing application** built with Nuxt 3, designed to help scientists analyze and work with academic papers using Large Language Models (LLMs). The application processes PDF papers, extracts content, generates embeddings, and provides AI-powered analysis.

## Technology Stack

### Frontend/Web Framework
- **Nuxt 3** - Full-stack Vue.js framework
- **Vue 3** with Composition API
- **TypeScript** throughout
- **TailwindCSS 4.x** for styling
- **Nuxt Auth Utils** for authentication

### Backend/API
- **Nuxt Server API** routes (file-based routing in `server/api/`)
- **Drizzle ORM** for database operations
- **Zod** for validation
- **PostgreSQL** database with pgvector for embeddings
- **S3-compatible storage** for file storage (MinIO/AWS S3)

### AI/ML Stack
- **Ollama** for local LLM inference
- **PDF processing** with unpdf and pdfjs-dist
- **Vector embeddings** with pgvector
- **LaTeX parsing** capabilities

### Development Tools
- **Bun** as package manager and runtime
- **Docker** for database and services
- **uv** for Python dependency management
- **Drizzle Kit** for database migrations
- **Prettier** for code formatting

## Architecture Patterns

### Monorepo Structure
- `/packages/` - Shared packages (database, ollama, arxiv, latex)
- `/modules/` - Python processing modules
- `/server/` - Nuxt server API routes
- `/app/` - Frontend Vue components and pages
- `/archive/` - Legacy Python Flask implementation

### Database Schema
- `users` - User management
- `papers` - Paper metadata and content
- `paper_embeddings` - Vector embeddings for semantic search
- `paper_references` - Paper citation relationships

### File Processing Pipeline
1. PDF upload via form data
2. File storage to S3
3. Text extraction (PDF → text)
4. LaTeX parsing if applicable
5. Content chunking and embedding generation
6. Database storage with vector search capabilities

## Key Development Patterns

### API Routes
- Follow RESTful conventions in `server/api/`
- Use Nuxt's `defineEventHandler` for route handlers
- Form data handling for file uploads
- Error handling with `createError`

### Database Operations
- Use Drizzle ORM with prepared statements
- PostgreSQL with pgvector extension for embeddings
- Migration-based schema management
- Proper indexing for vector similarity searches

### Component Architecture
- Design system components prefixed with `d-` (d-button, d-input, etc.)
- Composable-based state management
- TailwindCSS for styling with utility classes

### Environment Configuration
- Runtime config in `nuxt.config.ts`
- S3 credentials and database URLs via environment variables
- Development vs production environment handling

## Common Tasks & Workflows

### Adding New API Endpoints
1. Create file in `server/api/` following naming convention
2. Use `defineEventHandler` wrapper
3. Implement proper error handling and validation
4. Follow existing patterns for database operations

### Database Changes
1. Modify schema in `packages/database/schema.ts`
2. Generate migration: `bun run db:generate`
3. Apply migration: `bun run db:migrate`
4. Update related TypeScript types

### Frontend Components
1. Create in `app/components/` with appropriate naming
2. Use Composition API with `<script setup>`
3. Follow design system patterns
4. Include proper TypeScript typing

### Processing Modules
- Python modules in `/modules/` for heavy processing
- LaTeX parsing capabilities
- PDF text extraction
- Ollama integration for LLM processing

## Important Files & Directories

### Configuration
- `nuxt.config.ts` - Main Nuxt configuration
- `drizzle.config.ts` - Database configuration
- `package.json` - Dependencies and scripts
- `pyproject.toml` - Python dependencies

### Core Packages
- `packages/database/` - Database schema and utilities
- `packages/ollama/` - LLM integration
- `packages/arxiv/` - ArXiv API integration
- `packages/latex/` - LaTeX processing

### Key Scripts
- `scripts/setup.sh` - Environment setup
- `bun run dev` - Development server
- `bun run db:migrate` - Database migrations

## Development Best Practices

### Code Style
- Use TypeScript throughout
- Follow Vue 3 Composition API patterns
- Consistent naming conventions (camelCase for JS/TS, snake_case for DB)
- Proper error handling and validation

### Database Best Practices
- Use transactions for multi-step operations
- Implement proper indexing for queries
- Handle vector similarity searches efficiently
- Follow migration-based schema changes

### API Design
- RESTful endpoint design
- Proper HTTP status codes
- Consistent error response format
- Input validation with Zod schemas

### Security Considerations
- File upload validation and sanitization
- SQL injection prevention (via Drizzle ORM)
- Proper authentication middleware
- Environment variable management

## Common Pitfalls to Avoid

1. **File Processing**: Always validate file types and sizes before processing
2. **Vector Operations**: Ensure proper dimensions for embedding operations
3. **Database Connections**: Use connection pooling for production
4. **Memory Management**: Large PDF processing can be memory-intensive
5. **Error Handling**: Always provide meaningful error messages
6. **TypeScript**: Don't bypass type checking with `any`

## Testing & Debugging

### Available Test Files
- Test database operations, API routes, and processing modules
- Use proper test data and mocking

### Debugging Tips
- Check Docker containers for database connectivity
- Verify S3 configuration for file operations
- Monitor Ollama service for LLM operations
- Use Nuxt DevTools for frontend debugging

## Getting Started for Agents

1. **Setup**: Run `bun install` and `bun run setup` to run migrations and spin up docker containers for database and s3
2. **Database**: Ensure PostgreSQL with pgvector is running
3. **Services**: Start Ollama service for LLM operations
4. **Development**: Use `bun run dev` for development server
5. **Database Changes**: Always generate and run migrations

When making changes, always consider the full pipeline from file upload to AI processing and ensure compatibility across the TypeScript/Python bridge.
