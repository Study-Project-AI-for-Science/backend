// Minimal, hand-authored OpenAPI spec for current routes.
// You can later replace this with a zod-to-openapi generated spec.

export const openApiSpec = {
  openapi: "3.1.0",
  info: {
    title: "LLMs for Science Backend API",
    version: "1.0.0",
    description:
      "API for uploading, processing, and querying research papers, plus auth endpoints.",
  },
  servers: [{ url: "/" }],
  paths: {
    "/api": {
      get: {
        summary: "Health check",
        responses: {
          200: {
            description: "Service is healthy",
            content: { "application/json": { schema: { $ref: "#/components/schemas/Health" } } },
          },
        },
      },
    },
    "/api/login": {
      post: {
        summary: "Login",
        requestBody: {
          required: true,
          content: {
            "application/json": { schema: { $ref: "#/components/schemas/LoginRequest" } },
          },
        },
        responses: {
          200: {
            description: "Logged in",
            content: {
              "application/json": { schema: { $ref: "#/components/schemas/OkResponse" } },
            },
          },
          401: { description: "Invalid credentials" },
        },
      },
    },
    "/api/register": {
      post: {
        summary: "Register",
        requestBody: {
          required: true,
          content: {
            "application/json": { schema: { $ref: "#/components/schemas/RegisterRequest" } },
          },
        },
        responses: {
          200: {
            description: "Registered",
            content: {
              "application/json": { schema: { $ref: "#/components/schemas/OkResponse" } },
            },
          },
          400: { description: "Email already in use" },
        },
      },
    },
    "/api/papers": {
      get: {
        summary: "List papers",
        parameters: [
          { name: "page", in: "query", schema: { type: "integer", minimum: 1 } },
          { name: "pageSize", in: "query", schema: { type: "integer", minimum: 1, maximum: 1000 } },
          { name: "search", in: "query", schema: { type: "string" } },
        ],
        responses: {
          200: {
            description: "Paged results",
            content: {
              "application/json": { schema: { $ref: "#/components/schemas/PapersListResponse" } },
            },
          },
        },
      },
      post: {
        summary: "Upload a PDF",
        operationId: "uploadPaper",
        description:
          "Uploads a PDF and starts background processing (metadata extraction, text/LaTeX parsing, chunking, embeddings).\n\nBehavior:\n- New file hash: stores the file to S3, creates a `papers` row, and schedules background processing. Returns the Paper immediately (fields like `title` may be empty until processing completes).\n- Existing file hash + missing `documentExtractionResult`: reuses the existing row and re-triggers background processing. No re-upload occurs. Returns the existing Paper.\n- Existing file hash + present `documentExtractionResult`: returns the existing Paper unchanged; no reprocessing.\n\nPolling: clients typically poll `GET /api/papers/{id}` to observe updates.",
        requestBody: {
          required: true,
          content: {
            "multipart/form-data": {
              schema: {
                type: "object",
                required: ["file"],
                properties: { file: { type: "string", format: "binary" } },
              },
              examples: {
                curl: {
                  summary: "cURL upload",
                  value:
                    "curl -X POST http://localhost:3000/api/papers -F file=@paper.pdf",
                },
              },
            },
          },
        },
        responses: {
          200: {
            description:
              "Returns the Paper row (either newly created or existing). Background tasks may still be running.",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/Paper" },
                examples: {
                  newUpload: {
                    summary: "New file hash",
                    value: {
                      id: "01J123ABCDEF...",
                      title: "",
                      authors: "",
                      abstract: "",
                      fileHash: "sha256:...",
                      fileUrl: "http://minio.local/bucket/01J123ABCDEF",
                      onlineUrl: null,
                      content: null,
                      documentExtractionResult: null,
                    },
                  },
                  duplicateHandled: {
                    summary: "Existing file hash with processed data",
                    value: {
                      id: "01JEXISTING...",
                      title: "Attention Is All You Need",
                      authors: "Vaswani et al.",
                      abstract: "...",
                      fileHash: "sha256:...",
                      fileUrl: "http://minio.local/bucket/01JEXISTING...",
                      documentExtractionResult: "{ ... }",
                    },
                  },
                },
              },
            },
          },
          400: { description: "Invalid or missing file" },
        },
        "x-notes": {
          deduplication:
            "Deduplicates by SHA-256 of file contents. Duplicate uploads return the existing Paper.",
          backgroundProcessing:
            "Extraction and embeddings run async via event.waitUntil; DB is updated on completion.",
          reuploadBehavior:
            "If processing didn’t complete (no documentExtractionResult), a reupload restarts processing without reuploading to S3.",
        },
      },
    },
    "/api/papers/{id}": {
      get: {
        summary: "Get paper by ID",
        parameters: [
          { name: "id", in: "path", required: true, schema: { type: "string" } },
        ],
        responses: {
          200: {
            description: "Found",
            content: { "application/json": { schema: { $ref: "#/components/schemas/Paper" } } },
          },
          404: { description: "Not found" },
        },
      },
      put: {
        summary: "Update paper metadata",
        parameters: [
          { name: "id", in: "path", required: true, schema: { type: "string" } },
        ],
        requestBody: {
          required: true,
          content: {
            "application/json": { schema: { $ref: "#/components/schemas/PaperUpdate" } },
          },
        },
        responses: {
          200: {
            description: "Updated",
            content: { "application/json": { schema: { $ref: "#/components/schemas/Paper" } } },
          },
        },
      },
      delete: {
        summary: "Delete paper",
        parameters: [
          { name: "id", in: "path", required: true, schema: { type: "string" } },
        ],
        responses: {
          200: {
            description: "Deleted",
            content: { "application/json": { schema: { type: "object" } } },
          },
        },
      },
    },
    "/api/papers/{id}/references": {
      get: {
        summary: "List references for a paper",
        parameters: [
          { name: "id", in: "path", required: true, schema: { type: "string" } },
        ],
        responses: {
          200: {
            description: "References",
            content: {
              "application/json": {
                schema: { type: "array", items: { $ref: "#/components/schemas/PaperReference" } },
              },
            },
          },
        },
      },
    },
  },
  components: {
    schemas: {
      Health: {
        type: "object",
        properties: { status: { type: "string", example: "ok" } },
        required: ["status"],
      },
      OkResponse: {
        type: "object",
        properties: { ok: { type: "boolean", example: true } },
        required: ["ok"],
      },
      LoginRequest: {
        type: "object",
        properties: {
          email: { type: "string", format: "email" },
          password: { type: "string", minLength: 8 },
        },
        required: ["email", "password"],
      },
      RegisterRequest: {
        type: "object",
        properties: {
          name: { type: "string" },
          email: { type: "string", format: "email" },
          password: { type: "string", minLength: 8 },
        },
        required: ["name", "email", "password"],
      },
      Paper: {
        type: "object",
        properties: {
          id: { type: "string", example: "01HZX..." },
          title: { type: "string" },
          authors: { type: "string", description: "Comma-separated" },
          abstract: { type: "string" },
          fileHash: { type: "string" },
          fileUrl: { type: "string", format: "uri" },
          onlineUrl: { type: "string", nullable: true },
          content: { type: "string", nullable: true },
          documentExtractionResult: { type: "string", nullable: true, description: "JSON string" },
          publishedDate: { type: "string", nullable: true },
          createdAt: { type: "string", nullable: true },
          updatedAt: { type: "string", nullable: true },
          deletedAt: { type: "string", nullable: true },
        },
        required: ["id"],
      },
      PaperUpdate: {
        type: "object",
        properties: {
          title: { type: "string" },
          authors: { type: "string" },
          abstract: { type: "string" },
          paperUrl: { type: "string" },
          published: { type: "string" },
          updated: { type: "string" },
          markdownContent: { type: "string" },
        },
        additionalProperties: false,
      },
      PaperReference: {
        type: "object",
        properties: {
          id: { type: "string" },
          paperId: { type: "string" },
          referencePaperId: { type: "string", nullable: true },
          title: { type: "string" },
          authors: { type: "string" },
          raw_bibtex: { type: "string" },
          createdAt: { type: "string", nullable: true },
          updatedAt: { type: "string", nullable: true },
        },
        required: ["id", "paperId", "title"],
      },
      PapersListResponse: {
        type: "object",
        properties: {
          papers: { type: "array", items: { $ref: "#/components/schemas/Paper" } },
          total: { type: "integer", example: 42 },
        },
        required: ["papers", "total"],
      },
      Error: {
        type: "object",
        properties: {
          statusCode: { type: "integer" },
          statusMessage: { type: "string" },
        },
      },
    },
  },
} as const

export default openApiSpec
